#!/usr/bin/env python3
import argparse
import datetime
import html
import http.server
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.error
import urllib.request

PENDING_PATH = os.path.expanduser("~/.barkbridge/pending_replies.json")
CONTACTS_PATH = os.path.expanduser("~/.barkbridge/local_contacts.json")
HISTORY_PATH = os.path.expanduser("~/.barkbridge/local_history.json")
CONTACT_RULES_PATH = os.path.expanduser("~/.barkbridge/contact_rules.json")
SEND_LOCK = threading.Lock()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLICK_HELPER_SOURCE = os.path.join(SCRIPT_DIR, "mac-click.swift")
CLICK_HELPER_BIN = os.path.join(SCRIPT_DIR, "mac-click")
VISIBLE_CONTACTS = [
    "XQJ家庭群",
    "幸福一家人",
    "2026春节小聚群",
    "于磊",
    "薛启军工作号",
    "银河湾小院",
    "胖叔叔",
    "一方小院整修",
    "薛启军",
    "阳光8.3.2.",
    "可可",
    "微信ClawBot",
    "吴鹏好物捡漏群",
    "悍刀",
]
AMBIGUOUS_CONTACTS = {
    "家",
    "薛",
    "于磊",
}
DEFAULT_CONTACT_RULES = {
    "default_auto_send": False,
    "rules": {
        "XQJ家庭群": {"target": "XQJ家庭群", "auto_send": True},
        "薛启军工作号": {"target": "薛启军工作号", "auto_send": True},
        "一方小院整修": {"target": "一方小院整修", "auto_send": True},
        "幸福一家人": {"target": "幸福一家人", "auto_send": True},
        "2026春节小聚群": {"target": "2026春节小聚群", "auto_send": True},
        "悍刀": {"target": "悍刀", "auto_send": True},
        "薛启军": {"target": "薛启军", "auto_send": True},
        "银河湾小院": {"target": "银河湾小院", "auto_send": True},
        "罗虎、于磊": {"target": "罗虎、于磊", "auto_send": True},
        "胖叔叔": {"target": "胖叔叔", "auto_send": True},
        "可可": {"target": "可可", "auto_send": True},
        "微信ClawBot": {"target": "微信ClawBot", "auto_send": True},
        "吴鹏好物捡漏群": {"target": "吴鹏好物捡漏群", "auto_send": True},
        "家": {"target": "XQJ家庭群", "auto_send": False},
        "薛": {"target": "薛", "auto_send": False},
        "于磊": {"target": "于磊", "auto_send": False},
    },
}


def main():
    parser = argparse.ArgumentParser(description="Poll BarkBridge relay and send replies through Mac WeChat.")
    parser.add_argument("--poll-url", required=True, help="Relay poll URL, including secret query string.")
    parser.add_argument("--interval", type=int, default=1, help="Delay after each poll in seconds.")
    parser.add_argument("--receipt-url", default=os.environ.get("BARKBRIDGE_RECEIPT_URL", ""), help="Optional Bark endpoint URL for send receipts, for example https://api.day.app/key.")
    parser.add_argument("--max-retries", type=int, default=5, help="Maximum local retry attempts for failed sends.")
    parser.add_argument("--send-shortcut", choices=["enter", "cmd-enter", "both"], default="both", help="WeChat send shortcut to use after pasting the reply.")
    parser.add_argument("--web-host", default="127.0.0.1", help="Local web console host.")
    parser.add_argument("--web-port", type=int, default=8765, help="Local web console port.")
    parser.add_argument("--no-web", action="store_true", help="Disable local web console.")
    parser.add_argument("--once", action="store_true", help="Poll once and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print replies without operating WeChat.")
    args = parser.parse_args()

    if not args.no_web:
        start_web_console(args)

    while True:
        try:
            pending = load_pending()
            if pending:
                process_replies(pending, args)
            else:
                replies = fetch_replies(args.poll_url)
                process_replies(replies, args)
        except Exception as exc:
            print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)

        if args.once:
            return
        time.sleep(max(3, args.interval))


def start_web_console(args):
    handler = make_web_handler(args)
    server = http.server.ThreadingHTTPServer((args.web_host, args.web_port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"web: http://{args.web_host}:{args.web_port}/", flush=True)


def make_web_handler(args):
    class BarkBridgeWebHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *values):
            print(f"web: {self.address_string()} {fmt % values}", flush=True)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/":
                self.send_text(render_web_page(), "text/html; charset=utf-8")
                return
            if parsed.path == "/api/state":
                self.send_json({"contacts": load_contacts(), "history": load_history()})
                return
            self.send_error(404)

        def do_HEAD(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path not in ["/", "/api/state"]:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8" if parsed.path == "/" else "application/json; charset=utf-8")
            self.end_headers()

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/api/send":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length") or "0")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                contact = str(payload.get("contact") or "").strip()
                text = str(payload.get("text") or "").strip()
                if not contact or not text:
                    self.send_json({"ok": False, "error": "联系人和内容不能为空"}, status=400)
                    return
                add_contact(contact)
                append_history(contact, text, "sending")
                rule = resolve_contact_rule(contact)
                if not rule["auto_send"]:
                    stage_manual_review(contact, text, rule["target"])
                    append_history(contact, text, "manual-review")
                    send_receipt(args.receipt_url, "BarkBridge 未自动发送", f"{rule['reason']}，已复制内容，请在 Mac 微信手动确认: {contact} -> {rule['target']}")
                elif args.dry_run:
                    print(f"web dry-run: {contact}: {text}", flush=True)
                else:
                    with SEND_LOCK:
                        send_wechat(rule["target"], text, args.send_shortcut)
                    append_history(contact, text, "sent")
                self.send_json({"ok": True, "contacts": load_contacts(), "history": load_history()})
            except Exception as exc:
                append_history(str(locals().get("contact") or ""), str(locals().get("text") or ""), f"failed: {type(exc).__name__}: {exc}")
                self.send_json({"ok": False, "error": f"{type(exc).__name__}: {exc}", "history": load_history()}, status=500)

        def send_json(self, data, status=200):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_text(self, text, content_type, status=200):
            body = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return BarkBridgeWebHandler


def load_contacts():
    default_contacts = VISIBLE_CONTACTS + ["文件传输助手"]
    try:
        with open(CONTACTS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        contacts = [str(item).strip() for item in data if str(item).strip()]
    except FileNotFoundError:
        contacts = default_contacts
    except Exception as exc:
        print(f"error: failed to load local contacts: {exc}", file=sys.stderr, flush=True)
        contacts = default_contacts
    merged = []
    for contact in contacts + default_contacts:
        if contact and contact not in merged:
            merged.append(contact)
    return merged


def save_contacts(contacts):
    os.makedirs(os.path.dirname(CONTACTS_PATH), exist_ok=True)
    with open(CONTACTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(contacts, fh, ensure_ascii=False, indent=2)


def add_contact(contact):
    contacts = load_contacts()
    if contact not in contacts:
        contacts.insert(0, contact)
        save_contacts(contacts)


def load_history():
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data[-80:] if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception as exc:
        print(f"error: failed to load local history: {exc}", file=sys.stderr, flush=True)
        return []


def append_history(contact, text, status):
    if not contact and not text:
        return
    history = load_history()
    history.append({
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "contact": contact,
        "text": text,
        "status": status,
    })
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as fh:
        json.dump(history[-80:], fh, ensure_ascii=False, indent=2)


def render_web_page():
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BarkBridge 本地发送</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #111315;
      --panel: #1f2226;
      --panel-2: #2a2d31;
      --line: #34383d;
      --text: #f4f5f6;
      --muted: #a8adb3;
      --green: #07c160;
      --green-dark: #05a451;
      --bubble-in: #303337;
      --bubble-out: #12b969;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: #0d0f11;
      color: var(--text);
      font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      display: grid;
      place-items: center;
    }
    .shell {
      width: min(1120px, calc(100vw - 32px));
      height: min(760px, calc(100vh - 32px));
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      display: grid;
      grid-template-columns: 320px 1fr;
      box-shadow: 0 24px 80px rgb(0 0 0 / 0.45);
    }
    .sidebar {
      background: #202327;
      border-right: 1px solid var(--line);
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .search {
      padding: 16px;
      border-bottom: 1px solid var(--line);
    }
    .search input {
      width: 100%;
      height: 40px;
      border: 0;
      border-radius: 6px;
      background: #2d3035;
      color: var(--text);
      outline: none;
      padding: 0 12px;
      font-size: 14px;
    }
    .contacts {
      overflow: auto;
      padding: 8px 0;
    }
    .contact {
      width: 100%;
      border: 0;
      background: transparent;
      color: var(--text);
      display: flex;
      gap: 12px;
      align-items: center;
      text-align: left;
      padding: 12px 16px;
      cursor: pointer;
    }
    .contact:hover { background: #292d32; }
    .contact.active { background: #12a864; }
    .avatar {
      width: 42px;
      height: 42px;
      border-radius: 6px;
      background: linear-gradient(135deg, #4b6bfb, #10c77a);
      display: grid;
      place-items: center;
      font-weight: 700;
      flex: 0 0 auto;
    }
    .contact-name {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 15px;
    }
    .main {
      background: #1b1d20;
      display: grid;
      grid-template-rows: 64px 1fr 176px;
      min-width: 0;
    }
    .topbar {
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      padding: 0 24px;
      font-size: 18px;
      font-weight: 600;
    }
    .messages {
      overflow: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .empty {
      margin: auto;
      color: var(--muted);
    }
    .message {
      max-width: 76%;
      align-self: flex-end;
      display: grid;
      gap: 6px;
    }
    .bubble {
      background: var(--bubble-out);
      color: #06150c;
      border-radius: 8px 8px 2px 8px;
      padding: 10px 12px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-size: 15px;
    }
    .meta {
      color: var(--muted);
      font-size: 12px;
      text-align: right;
    }
    .composer {
      border-top: 1px solid var(--line);
      background: #202327;
      display: grid;
      grid-template-rows: 1fr 48px;
      padding: 12px 16px 14px;
      gap: 10px;
    }
    textarea {
      width: 100%;
      resize: none;
      border: 0;
      outline: none;
      background: transparent;
      color: var(--text);
      font: inherit;
      font-size: 15px;
      line-height: 1.5;
    }
    .composer-bottom {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .manual-contact {
      width: 220px;
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel-2);
      color: var(--text);
      outline: none;
      padding: 0 10px;
    }
    .send {
      height: 36px;
      min-width: 96px;
      border: 0;
      border-radius: 6px;
      background: var(--green);
      color: #04150b;
      font-weight: 700;
      cursor: pointer;
    }
    .send:disabled {
      opacity: 0.55;
      cursor: default;
    }
    .status { color: var(--muted); font-size: 13px; }
    @media (max-width: 780px) {
      .shell {
        width: 100vw;
        height: 100vh;
        border-radius: 0;
        grid-template-columns: 132px 1fr;
      }
      .contact { padding: 10px; }
      .avatar { display: none; }
      .manual-contact { width: 150px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="search"><input id="contactInput" placeholder="输入联系人并加入左侧"></div>
      <div class="contacts" id="contacts"></div>
    </aside>
    <main class="main">
      <div class="topbar" id="title">选择联系人</div>
      <div class="messages" id="messages"><div class="empty">选择左侧联系人后发送消息</div></div>
      <form class="composer" id="form">
        <textarea id="text" placeholder="输入要通过 Mac 微信发送的内容"></textarea>
        <div class="composer-bottom">
          <input class="manual-contact" id="manualContact" placeholder="联系人">
          <div class="status" id="status">本地连接中</div>
          <button class="send" id="send" type="submit">发送</button>
        </div>
      </form>
    </main>
  </div>
  <script>
    let contacts = [];
    let history = [];
    let selected = "";

    const contactsEl = document.getElementById("contacts");
    const titleEl = document.getElementById("title");
    const messagesEl = document.getElementById("messages");
    const textEl = document.getElementById("text");
    const statusEl = document.getElementById("status");
    const sendEl = document.getElementById("send");
    const contactInputEl = document.getElementById("contactInput");
    const manualContactEl = document.getElementById("manualContact");

    function esc(value) {
      return String(value).replace(/[&<>"']/g, ch => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[ch]));
    }

    function renderContacts() {
      contactsEl.innerHTML = contacts.map(contact => `
        <button class="contact ${contact === selected ? "active" : ""}" data-contact="${esc(contact)}">
          <div class="avatar">${esc(contact.slice(0, 1))}</div>
          <div class="contact-name">${esc(contact)}</div>
        </button>
      `).join("");
      contactsEl.querySelectorAll(".contact").forEach(button => {
        button.addEventListener("click", () => selectContact(button.dataset.contact));
      });
    }

    function renderMessages() {
      titleEl.textContent = selected || "选择联系人";
      manualContactEl.value = selected;
      const items = history.filter(item => item.contact === selected);
      if (!selected || items.length === 0) {
        messagesEl.innerHTML = `<div class="empty">${selected ? "还没有本地发送记录" : "选择左侧联系人后发送消息"}</div>`;
        return;
      }
      messagesEl.innerHTML = items.map(item => `
        <div class="message">
          <div class="bubble">${esc(item.text)}</div>
          <div class="meta">${esc(item.time)} · ${esc(item.status)}</div>
        </div>
      `).join("");
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function selectContact(contact) {
      selected = contact;
      renderContacts();
      renderMessages();
      textEl.focus();
    }

    async function refresh() {
      const response = await fetch("/api/state");
      const data = await response.json();
      contacts = data.contacts || [];
      history = data.history || [];
      if (!selected && contacts.length) selected = contacts[0];
      renderContacts();
      renderMessages();
      statusEl.textContent = "已连接本地 Mac relay";
    }

    document.getElementById("form").addEventListener("submit", async event => {
      event.preventDefault();
      const contact = manualContactEl.value.trim() || selected;
      const text = textEl.value.trim();
      if (!contact || !text) {
        statusEl.textContent = "联系人和内容不能为空";
        return;
      }
      sendEl.disabled = true;
      statusEl.textContent = "正在调用 Mac 微信";
      try {
        const response = await fetch("/api/send", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({contact, text})
        });
        const data = await response.json();
        if (!data.ok) throw new Error(data.error || "发送失败");
        contacts = data.contacts || contacts;
        history = data.history || history;
        selected = contact;
        textEl.value = "";
        renderContacts();
        renderMessages();
        statusEl.textContent = "已执行发送动作";
      } catch (error) {
        statusEl.textContent = error.message;
      } finally {
        sendEl.disabled = false;
      }
    });

    contactInputEl.addEventListener("keydown", event => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      const contact = contactInputEl.value.trim();
      if (!contact) return;
      if (!contacts.includes(contact)) contacts.unshift(contact);
      contactInputEl.value = "";
      selectContact(contact);
    });

    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>"""


def fetch_replies(poll_url):
    request = urllib.request.Request(poll_url, headers={"User-Agent": "BarkBridge-MacRelay/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:300]}") from exc
    if isinstance(payload, list):
        return payload
    return payload.get("replies") or []


def process_replies(replies, args):
    if not replies:
        return
    remaining = []
    for reply in replies:
        normalized = normalize_reply(reply)
        contact = normalized["contact"]
        text = normalized["text"]
        attempts = normalized["attempts"]
        if not contact or not text:
            print(f"skip invalid reply: {reply}", flush=True)
            continue
        print(f"picked: {contact}: {text[:40]}", flush=True)
        if args.dry_run:
            print(f"dry-run: {contact}: {text}", flush=True)
            continue
        rule = resolve_contact_rule(contact)
        if not rule["auto_send"]:
            stage_manual_review(contact, text, rule["target"])
            print(f"manual-review: {contact} -> {rule['target']} ({rule['reason']})", flush=True)
            send_receipt(args.receipt_url, "BarkBridge 未自动发送", f"{rule['reason']}，已复制内容，请在 Mac 微信手动确认: {contact} -> {rule['target']}")
            continue
        try:
            with SEND_LOCK:
                send_wechat(rule["target"], text, args.send_shortcut)
            print(f"sent-action: {contact} -> {rule['target']}", flush=True)
        except Exception as exc:
            normalized["attempts"] = attempts + 1
            normalized["last_error"] = f"{type(exc).__name__}: {exc}"
            if normalized["attempts"] <= args.max_retries:
                remaining.append(normalized)
                print(f"queued retry {normalized['attempts']}/{args.max_retries}: {contact}", file=sys.stderr, flush=True)
            else:
                print(f"drop after retries: {contact}: {normalized['last_error']}", file=sys.stderr, flush=True)
            send_receipt(args.receipt_url, "BarkBridge 回复失败", f"{contact}: {normalized['last_error']}")
    save_pending(remaining)


def normalize_reply(reply):
    return {
        "id": str(reply.get("id") or f"local-{int(time.time() * 1000)}"),
        "token": str(reply.get("token") or ""),
        "contact": str(reply.get("contact") or "").strip(),
        "text": str(reply.get("text") or "").strip(),
        "attempts": int(reply.get("attempts") or 0),
        "last_error": str(reply.get("last_error") or ""),
    }


def ensure_contact_rules():
    if os.path.exists(CONTACT_RULES_PATH):
        return
    os.makedirs(os.path.dirname(CONTACT_RULES_PATH), exist_ok=True)
    with open(CONTACT_RULES_PATH, "w", encoding="utf-8") as fh:
        json.dump(DEFAULT_CONTACT_RULES, fh, ensure_ascii=False, indent=2)


def load_contact_rules():
    ensure_contact_rules()
    try:
        with open(CONTACT_RULES_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("contact rules root must be an object")
        rules = data.get("rules")
        if not isinstance(rules, dict):
            data["rules"] = {}
        return data
    except Exception as exc:
        print(f"error: failed to load contact rules: {exc}", file=sys.stderr, flush=True)
        return DEFAULT_CONTACT_RULES


def resolve_contact_rule(contact):
    contact = str(contact or "").strip()
    data = load_contact_rules()
    raw_rule = data.get("rules", {}).get(contact)
    if isinstance(raw_rule, dict):
        target = str(raw_rule.get("target") or contact).strip() or contact
        auto_send = bool(raw_rule.get("auto_send"))
        return {
            "target": target,
            "auto_send": auto_send,
            "reason": "联系人规则要求人工确认" if not auto_send else "联系人规则允许自动发送",
        }
    if is_risky_contact_name(contact):
        return {
            "target": contact,
            "auto_send": False,
            "reason": "联系人名称过短或不唯一，未配置规则",
        }
    auto_send = bool(data.get("default_auto_send"))
    return {
        "target": contact,
        "auto_send": auto_send,
        "reason": "默认规则允许自动发送" if auto_send else "默认规则要求人工确认",
    }


def is_risky_contact_name(contact):
    contact = str(contact or "").strip()
    return contact in AMBIGUOUS_CONTACTS or len(contact) <= 1


def stage_manual_review(contact, text, target=None):
    target = str(target or contact).strip()
    payload = f"通知联系人: {contact}\nMac 微信目标: {target}\n内容: {text}"
    script = r'''
on run argv
  set the clipboard to item 1 of argv
end run
'''
    subprocess.run([osascript_bin(), "-e", script, payload], check=True, timeout=10)


def load_pending():
    try:
        with open(PENDING_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception as exc:
        print(f"error: failed to load pending replies: {exc}", file=sys.stderr, flush=True)
        return []


def save_pending(replies):
    os.makedirs(os.path.dirname(PENDING_PATH), exist_ok=True)
    with open(PENDING_PATH, "w", encoding="utf-8") as fh:
        json.dump(replies, fh, ensure_ascii=False, indent=2)


def send_receipt(receipt_url, title, body):
    if not receipt_url:
        return
    base = receipt_url.rstrip("/")
    url = f"{base}/{urllib.parse.quote(title)}/{urllib.parse.quote(body)}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "BarkBridge-MacRelay/1.0"})
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except Exception as exc:
        print(f"receipt error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)


def send_wechat(contact, text, send_shortcut):
    bounds = get_wechat_window_bounds()
    if contact in VISIBLE_CONTACTS:
        select_visible_contact(contact, bounds)
    else:
        select_contact_by_search(contact, bounds)
    click_message_input(bounds)
    paste_and_send(text, send_shortcut)


def osascript_bin():
    bundled = "/Applications/BarkBridgeOsascript.app/Contents/MacOS/BarkBridgeOsascript"
    if os.path.exists(bundled):
        return bundled
    return "/usr/bin/osascript"


def get_wechat_window_bounds():
    script = r'''
on run argv
  tell application "WeChat"
    activate
    try
      reopen
    end try
  end tell
  delay 1

  tell application "System Events"
    tell process "WeChat"
      set frontmost to true
      try
        set value of attribute "AXMinimized" of window 1 to false
      end try
      try
        set position of window 1 to {0, 0}
        set size of window 1 to {1440, 900}
      end try
      delay 0.2

      set windowPosition to position of window 1
      set windowLeft to item 1 of windowPosition
      set windowTop to item 2 of windowPosition
      set windowSize to size of window 1
      set windowWidth to item 1 of windowSize
      set windowHeight to item 2 of windowSize
      return (windowLeft as text) & "," & (windowTop as text) & "," & (windowWidth as text) & "," & (windowHeight as text)
    end tell
  end tell
end run
'''
    result = subprocess.run([osascript_bin(), "-e", script], check=True, capture_output=True, text=True, timeout=10)
    parts = [int(float(part.strip())) for part in result.stdout.strip().split(",")]
    if len(parts) != 4:
        raise RuntimeError(f"unexpected WeChat window bounds: {result.stdout!r}")
    return {"left": parts[0], "top": parts[1], "width": parts[2], "height": parts[3]}


def select_visible_contact(contact, bounds):
    index = VISIBLE_CONTACTS.index(contact)
    # The visible contact list is pinned on the left. Normalizing the WeChat
    # window above keeps these row coordinates stable and avoids search hits.
    click_at(bounds["left"] + 240, bounds["top"] + 98 + (index * 90))
    time.sleep(0.8)


def ensure_click_helper():
    if os.path.exists(CLICK_HELPER_BIN) and os.path.getmtime(CLICK_HELPER_BIN) >= os.path.getmtime(CLICK_HELPER_SOURCE):
        return
    subprocess.run(["/usr/bin/swiftc", CLICK_HELPER_SOURCE, "-o", CLICK_HELPER_BIN], check=True, timeout=30)


def click_at(x, y):
    ensure_click_helper()
    subprocess.run([CLICK_HELPER_BIN, str(int(x)), str(int(y))], check=True, timeout=5)


def select_contact_by_search(contact, bounds):
    click_at(bounds["left"] + 150, bounds["top"] + 28)
    time.sleep(0.2)
    script = r'''
on run argv
  set contactName to item 1 of argv
  tell application "System Events"
    set the clipboard to contactName
    keystroke "a" using command down
    delay 0.1
    keystroke "v" using command down
  end tell
end run
'''
    subprocess.run([osascript_bin(), "-e", script, contact], check=True, timeout=10)
    time.sleep(0.9)
    script = r'''
on run argv
  tell application "System Events"
    key code 125
    delay 0.1
    key code 36
  end tell
end run
'''
    subprocess.run([osascript_bin(), "-e", script], check=True, timeout=10)
    time.sleep(0.9)


def click_message_input(bounds):
    click_at(bounds["left"] + (bounds["width"] * 0.55), bounds["top"] + bounds["height"] - 55)
    time.sleep(0.2)


def paste_and_send(text, send_shortcut):
    script = r'''
on run argv
  set replyText to item 1 of argv
  set sendShortcut to item 2 of argv

  try
    set previousClipboard to the clipboard as text
  on error
    set previousClipboard to ""
  end try

  tell application "System Events"
    keystroke "a" using command down
    delay 0.1
    set the clipboard to replyText
    keystroke "v" using command down
    delay 0.4
    if sendShortcut is "cmd-enter" then
      key code 36 using command down
    else if sendShortcut is "both" then
      key code 36
      delay 0.4
      key code 36 using command down
    else
      key code 36
    end if
  end tell

  delay 0.2
  set the clipboard to previousClipboard
end run
'''
    subprocess.run([osascript_bin(), "-e", script, text, send_shortcut], check=True, timeout=15)


if __name__ == "__main__":
    main()
