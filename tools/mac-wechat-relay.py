#!/usr/bin/env python3
import argparse
import datetime
import html
import http.client
import http.server
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.error
import urllib.request

PENDING_PATH = os.path.expanduser("~/.barkbridge/pending_replies.json")
CONTACTS_PATH = os.path.expanduser("~/.barkbridge/local_contacts.json")
HISTORY_PATH = os.path.expanduser("~/.barkbridge/local_history.json")
CONTACT_RULES_PATH = os.path.expanduser("~/.barkbridge/contact_rules.json")
PROCESSED_PATH = os.path.expanduser("~/.barkbridge/processed_replies.json")
CONTROL_PATH = os.path.expanduser("~/.barkbridge/control.json")
SEND_LOCK = threading.Lock()
POLL_ERROR_LOG_EVERY_SECONDS = 60
FAILURE_PAUSE_THRESHOLD = 3
CONTACT_FAILURES = {}
RELAY_STATUS = {
    "started_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "worker_wait_ms": None,
    "poll_timeout": None,
    "poll_mode": "initializing",
    "last_poll_at": "",
    "last_reply_at": "",
    "last_send_at": "",
    "last_success": "",
    "last_error": "",
    "last_identified_title": "",
}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLICK_HELPER_SOURCE = os.path.join(SCRIPT_DIR, "mac-click.swift")
CLICK_HELPER_BIN = os.path.join(SCRIPT_DIR, "mac-click")
OCR_HELPER_SOURCE = os.path.join(SCRIPT_DIR, "mac-ocr.swift")
OCR_HELPER_BIN = os.path.join(SCRIPT_DIR, "mac-ocr")
OCR_BOXES_HELPER_SOURCE = os.path.join(SCRIPT_DIR, "mac-ocr-boxes.swift")
OCR_BOXES_HELPER_BIN = os.path.join(SCRIPT_DIR, "mac-ocr-boxes")
VISIBLE_CONTACTS = [
    "XQJ家庭群",
    "幸福一家人",
    "2026春节小聚群",
    "于磊",
    "薛启军工作号",
    "薛启军",
    "悍刀",
    "银河湾小院",
    "一方小院整修",
    "胖叔叔",
    "阳光8.3.2.",
    "可可",
    "吴鹏好物捡漏群",
    "罗虎、于磊",
    "家",
]
AMBIGUOUS_CONTACTS = {
    "家",
    "薛",
    "于磊",
}
COMMAND_ADAPTER_TARGETS = {
    "微信ClawBot",
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
        "微信ClawBot": {"target": "微信ClawBot", "auto_send": False},
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
    parser.add_argument("--poll-timeout", type=int, default=0, help="HTTP timeout for relay polling in seconds. 0 means auto-detect.")
    parser.add_argument("--worker-wait-ms", type=int, default=-1, help="Worker long-poll wait time in milliseconds. -1 means auto-detect, 0 means immediate polling.")
    parser.add_argument("--receipt-url", default=os.environ.get("BARKBRIDGE_RECEIPT_URL", ""), help="Optional Bark endpoint URL for send receipts, for example https://api.day.app/key.")
    parser.add_argument("--ingest-url", default=os.environ.get("BARKBRIDGE_INGEST_URL", ""), help="Optional relay ingest URL for writing voice transcription results. Defaults to /ingest derived from --poll-url.")
    parser.add_argument("--enable-voice-transcribe", action="store_true", help="Enable experimental Mac WeChat voice-to-text UI automation. Disabled by default because current Mac WeChat exposes neither chat Accessibility elements nor plain voice files.")
    parser.add_argument("--disable-voice-transcribe", action="store_true", help="Disable experimental Mac WeChat voice-to-text tasks. Kept for compatibility; voice transcription is disabled by default.")
    parser.add_argument("--voice-max-retries", type=int, default=1, help="Maximum local retry attempts for experimental voice-to-text tasks.")
    parser.add_argument("--voice-task-ttl-minutes", type=int, default=10, help="Drop voice-to-text tasks older than this many minutes.")
    parser.add_argument("--voice-click-limit", type=int, default=24, help="Maximum voice bubble click probes per voice task.")
    parser.add_argument("--voice-menu-limit", type=int, default=12, help="Maximum voice context-menu probes per voice task.")
    parser.add_argument("--voice-probe-timeout", type=float, default=0.8, help="Seconds to wait after each voice click probe.")
    parser.add_argument("--voice-final-timeout", type=float, default=5.0, help="Seconds to wait after clicking the voice-to-text menu item.")
    parser.add_argument("--voice-left-click-first", action="store_true", help="Try left-click OCR probes before the context-menu path. Disabled by default to avoid long OCR scans.")
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

    configure_poll_mode(args)
    print(f"relay config: poll={args.poll_url} receipt={args.receipt_url or '-'}", flush=True)

    last_poll_error = ""
    last_poll_error_time = 0.0
    poll_error_count = 0
    while True:
        try:
            pending = load_pending()
            if pending:
                process_replies(pending, args)
            else:
                replies = fetch_replies(args.poll_url, args.poll_timeout, args.worker_wait_ms)
                process_replies(replies, args)
            last_poll_error = ""
            poll_error_count = 0
        except PollNetworkError as exc:
            poll_error_count += 1
            now = time.time()
            message = str(exc)
            if message != last_poll_error or now - last_poll_error_time >= POLL_ERROR_LOG_EVERY_SECONDS:
                print(f"poll warning ({poll_error_count}): {message}", file=sys.stderr, flush=True)
                last_poll_error = message
                last_poll_error_time = now
        except Exception as exc:
            print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)

        if args.once:
            return
        time.sleep(max(3, args.interval))


def start_web_console(args):
    handler = make_web_handler(args)
    try:
        server = http.server.ThreadingHTTPServer((args.web_host, args.web_port), handler)
    except OSError as exc:
        print(f"web disabled: http://{args.web_host}:{args.web_port}/ unavailable: {exc}", file=sys.stderr, flush=True)
        return
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
                self.send_json(build_state())
                return
            if parsed.path == "/api/rules":
                self.send_json(load_contact_rules())
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
            if parsed.path == "/api/control":
                self.handle_control_post()
                return
            if parsed.path == "/api/rules":
                self.handle_rules_post()
                return
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
                control = load_control()
                if control["paused"] or control["manual_only"] or not control["auto_send_enabled"]:
                    stage_manual_review(contact, text, rule["target"])
                    reason = control_pause_reason(control)
                    append_history(contact, text, f"manual-review: {reason}")
                    send_receipt(args.receipt_url, "BarkBridge 未自动发送", f"{reason}，已复制内容，请在 Mac 微信手动确认: {contact} -> {rule['target']}")
                elif not rule["auto_send"]:
                    stage_manual_review(contact, text, rule["target"])
                    append_history(contact, text, "manual-review")
                    send_receipt(args.receipt_url, "BarkBridge 未自动发送", f"{rule['reason']}，已复制内容，请在 Mac 微信手动确认: {contact} -> {rule['target']}")
                elif args.dry_run:
                    print(f"web dry-run: {contact}: {text}", flush=True)
                else:
                    with SEND_LOCK:
                        result = send_wechat(rule["target"], text, args.send_shortcut, rule)
                    append_history(contact, text, f"sent: {result['actual_title']}")
                    CONTACT_FAILURES.pop(rule["target"], None)
                    update_status(last_reply_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), last_send_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), last_success=f"{contact} -> {rule['target']}", last_identified_title=result["actual_title"], last_error="")
                    send_receipt(args.receipt_url, "BarkBridge 已发送", format_receipt(contact, rule["target"], result["actual_title"], text))
                self.send_json({"ok": True, "contacts": load_contacts(), "history": load_history()})
            except Exception as exc:
                note_contact_failure(str(locals().get("contact") or ""))
                update_status(last_error=f"{locals().get('contact') or ''}: {type(exc).__name__}: {exc}")
                append_history(str(locals().get("contact") or ""), str(locals().get("text") or ""), f"failed: {type(exc).__name__}: {exc}")
                self.send_json({"ok": False, "error": f"{type(exc).__name__}: {exc}", "history": load_history()}, status=500)

        def handle_control_post(self):
            try:
                length = int(self.headers.get("Content-Length") or "0")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                control = load_control()
                for key in ["paused", "auto_send_enabled", "manual_only"]:
                    if key in payload:
                        control[key] = bool(payload.get(key))
                if "note" in payload:
                    control["note"] = str(payload.get("note") or "").strip()
                save_control(control)
                self.send_json({"ok": True, "control": control, "state": build_state()})
            except Exception as exc:
                self.send_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, status=500)

        def handle_rules_post(self):
            try:
                length = int(self.headers.get("Content-Length") or "0")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                rules = load_contact_rules()
                contact = str(payload.get("contact") or "").strip()
                if not contact:
                    self.send_json({"ok": False, "error": "联系人不能为空"}, status=400)
                    return
                rule = {
                    "target": str(payload.get("target") or contact).strip() or contact,
                    "auto_send": bool(payload.get("auto_send")),
                    "require_exact_title": payload.get("require_exact_title", True) is not False,
                }
                aliases = payload.get("aliases", [])
                if isinstance(aliases, str):
                    aliases = [item.strip() for item in aliases.replace("，", ",").split(",")]
                rule["aliases"] = [str(item).strip() for item in aliases if str(item).strip()]
                note = str(payload.get("note") or "").strip()
                if note:
                    rule["note"] = note
                rules.setdefault("rules", {})[contact] = rule
                save_contact_rules(rules)
                add_contact(contact)
                self.send_json({"ok": True, "rules": rules, "state": build_state()})
            except Exception as exc:
                self.send_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, status=500)

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


def build_state():
    control = load_control()
    history = load_history()
    return {
        "contacts": load_contacts(),
        "history": history,
        "rules": load_contact_rules(),
        "control": control,
        "status": {
            **RELAY_STATUS,
            "pending_count": len(load_pending()),
            "history_count": len(history),
            "processed_count": len(load_processed()),
            "failure_counts": CONTACT_FAILURES,
        },
    }


def update_status(**values):
    RELAY_STATUS.update({key: value for key, value in values.items() if value is not None})


def default_control():
    return {
        "paused": False,
        "auto_send_enabled": True,
        "manual_only": False,
        "note": "",
    }


def load_control():
    try:
        with open(CONTROL_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("control root must be object")
    except FileNotFoundError:
        data = {}
    except Exception as exc:
        print(f"error: failed to load control: {exc}", file=sys.stderr, flush=True)
        data = {}
    control = default_control()
    control.update({key: data.get(key, control[key]) for key in control})
    return control


def save_control(control):
    os.makedirs(os.path.dirname(CONTROL_PATH), exist_ok=True)
    normalized = default_control()
    normalized.update({key: control.get(key, normalized[key]) for key in normalized})
    with open(CONTROL_PATH, "w", encoding="utf-8") as fh:
        json.dump(normalized, fh, ensure_ascii=False, indent=2)


def control_pause_reason(control):
    if control.get("paused"):
        return "Mac relay 已暂停"
    if control.get("manual_only"):
        return "当前为仅手动模式"
    if not control.get("auto_send_enabled", True):
        return "自动发送总开关已关闭"
    return "控制规则要求人工确认"


def note_contact_failure(target):
    target = str(target or "").strip()
    if not target:
        return
    CONTACT_FAILURES[target] = CONTACT_FAILURES.get(target, 0) + 1
    if CONTACT_FAILURES[target] < FAILURE_PAUSE_THRESHOLD:
        return
    rules = load_contact_rules()
    raw_rules = rules.setdefault("rules", {})
    matched_key = None
    for key, rule in raw_rules.items():
        if isinstance(rule, dict) and str(rule.get("target") or key).strip() == target:
            matched_key = key
            break
    if not matched_key:
        matched_key = target
    rule = raw_rules.get(matched_key) if isinstance(raw_rules.get(matched_key), dict) else {"target": target}
    rule["target"] = str(rule.get("target") or target).strip() or target
    rule["auto_send"] = False
    rule["require_exact_title"] = rule.get("require_exact_title", True) is not False
    rule["note"] = f"连续失败 {CONTACT_FAILURES[target]} 次，已自动暂停自动发送"
    raw_rules[matched_key] = rule
    save_contact_rules(rules)
    update_status(last_error=f"{target} 连续失败 {CONTACT_FAILURES[target]} 次，已自动暂停")


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
  <title>BarkBridge Mac 控制台</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101214;
      --panel: #1f2226;
      --panel-2: #292d31;
      --line: #34383d;
      --text: #f4f5f6;
      --muted: #a8adb3;
      --green: #07c160;
      --red: #ff5f57;
      --amber: #f2b84b;
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; background: #0d0f11; color: var(--text); font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .page { max-width: 1280px; margin: 0 auto; padding: 18px; display: grid; gap: 14px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    h1 { margin: 0; font-size: 22px; }
    .subtle { color: var(--muted); font-size: 13px; }
    .grid { display: grid; grid-template-columns: 360px 1fr; gap: 14px; align-items: start; }
    .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    .panel h2 { margin: 0; padding: 14px 16px; font-size: 15px; border-bottom: 1px solid var(--line); }
    .panel-body { padding: 14px 16px; display: grid; gap: 12px; }
    .status-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .metric { background: var(--panel-2); border-radius: 8px; padding: 10px; min-width: 0; }
    .metric strong { display: block; font-size: 18px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .metric span { color: var(--muted); font-size: 12px; }
    .switches { display: grid; gap: 8px; }
    label.switch { display: flex; align-items: center; justify-content: space-between; gap: 12px; background: var(--panel-2); border-radius: 8px; padding: 10px 12px; }
    input, textarea, select { width: 100%; border: 1px solid var(--line); border-radius: 6px; background: var(--panel-2); color: var(--text); outline: none; padding: 9px 10px; font: inherit; }
    textarea { min-height: 88px; resize: vertical; line-height: 1.5; }
    button { border: 0; border-radius: 6px; background: var(--green); color: #04150b; font-weight: 800; height: 36px; padding: 0 14px; cursor: pointer; }
    button.secondary { background: var(--panel-2); color: var(--text); border: 1px solid var(--line); }
    button.danger { background: var(--red); color: #190505; }
    .contacts { max-height: 360px; overflow: auto; display: grid; gap: 6px; }
    .contact { width: 100%; min-width: 0; text-align: left; background: transparent; color: var(--text); border: 1px solid transparent; border-radius: 6px; padding: 9px 10px; display: grid; grid-template-columns: 1fr auto; gap: 8px; }
    .contact.active { background: #12a864; color: #03150a; }
    .badge { font-size: 12px; color: var(--muted); }
    .contact.active .badge { color: #073b1f; }
    .tabs { display: flex; gap: 8px; padding: 10px; border-bottom: 1px solid var(--line); }
    .tab { background: var(--panel-2); color: var(--text); border: 1px solid var(--line); }
    .tab.active { background: var(--green); color: #03150a; }
    .view { display: none; }
    .view.active { display: block; }
    .history { max-height: 540px; overflow: auto; display: grid; gap: 8px; }
    .event { background: var(--panel-2); border-radius: 8px; padding: 10px 12px; }
    .event-top { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 6px; color: var(--muted); font-size: 12px; }
    .event-text { white-space: pre-wrap; overflow-wrap: anywhere; }
    .form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .full { grid-column: 1 / -1; }
    @media (max-width: 860px) {
      .page { padding: 10px; }
      .grid { grid-template-columns: 1fr; }
      .status-grid, .form-grid { grid-template-columns: 1fr; }
      header { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <div class="page">
    <header>
      <div>
        <h1>BarkBridge Mac 控制台</h1>
        <div class="subtle" id="summary">正在连接本地 relay</div>
      </div>
      <button class="secondary" id="refreshBtn" type="button">刷新</button>
    </header>

    <section class="panel">
      <h2>运行状态</h2>
      <div class="panel-body">
        <div class="status-grid" id="metrics"></div>
        <div class="switches">
          <label class="switch"><span>暂停 relay</span><input id="paused" type="checkbox"></label>
          <label class="switch"><span>允许自动发送</span><input id="autoSendEnabled" type="checkbox"></label>
          <label class="switch"><span>仅手动模式</span><input id="manualOnly" type="checkbox"></label>
        </div>
      </div>
    </section>

    <div class="grid">
      <section class="panel">
        <h2>联系人</h2>
        <div class="panel-body">
          <input id="contactSearch" placeholder="搜索或输入联系人">
          <div class="contacts" id="contacts"></div>
        </div>
      </section>

      <section class="panel">
        <div class="tabs">
          <button class="tab active" data-view="sendView" type="button">发送</button>
          <button class="tab" data-view="ruleView" type="button">规则</button>
          <button class="tab" data-view="historyView" type="button">审计</button>
        </div>
        <div class="panel-body">
          <div class="view active" id="sendView">
            <form id="sendForm" class="form-grid">
              <input id="manualContact" placeholder="联系人">
              <button type="submit">发送到 Mac 微信</button>
              <textarea class="full" id="text" placeholder="输入要发送的内容"></textarea>
              <div class="subtle full" id="sendStatus">选择联系人后发送</div>
            </form>
          </div>
          <div class="view" id="ruleView">
            <form id="ruleForm" class="form-grid">
              <input id="ruleContact" placeholder="通知联系人">
              <input id="ruleTarget" placeholder="Mac 微信目标">
              <input id="ruleAliases" class="full" placeholder="别名，用逗号分隔">
              <label class="switch full"><span>允许自动发送</span><input id="ruleAutoSend" type="checkbox"></label>
              <label class="switch full"><span>要求标题精确校验</span><input id="ruleExactTitle" type="checkbox" checked></label>
              <input id="ruleNote" class="full" placeholder="备注">
              <button type="submit">保存规则</button>
            </form>
          </div>
          <div class="view" id="historyView">
            <div class="history" id="history"></div>
          </div>
        </div>
      </section>
    </div>
  </div>
  <script>
    let contacts = [];
    let history = [];
    let selected = "";
    let state = {};

    const contactsEl = document.getElementById("contacts");
    const textEl = document.getElementById("text");
    const sendStatusEl = document.getElementById("sendStatus");
    const contactSearchEl = document.getElementById("contactSearch");
    const manualContactEl = document.getElementById("manualContact");
    const metricsEl = document.getElementById("metrics");
    const historyEl = document.getElementById("history");

    function esc(value) {
      return String(value).replace(/[&<>"']/g, ch => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[ch]));
    }

    function renderContacts() {
      const query = contactSearchEl.value.trim().toLowerCase();
      const rules = (state.rules && state.rules.rules) || {};
      const visible = contacts.filter(contact => !query || contact.toLowerCase().includes(query));
      contactsEl.innerHTML = visible.map(contact => {
        const rule = rules[contact] || {};
        const badge = rule.auto_send ? "自动" : "手动";
        return `
        <button class="contact ${contact === selected ? "active" : ""}" data-contact="${esc(contact)}" type="button">
          <span>${esc(contact)}</span><span class="badge">${badge}</span>
        </button>
      `}).join("");
      contactsEl.querySelectorAll(".contact").forEach(button => {
        button.addEventListener("click", () => selectContact(button.dataset.contact));
      });
    }

    function renderStatus() {
      const status = state.status || {};
      const control = state.control || {};
      document.getElementById("summary").textContent = control.paused ? "已暂停" : (control.manual_only ? "仅手动模式" : "运行中");
      document.getElementById("paused").checked = !!control.paused;
      document.getElementById("autoSendEnabled").checked = control.auto_send_enabled !== false;
      document.getElementById("manualOnly").checked = !!control.manual_only;
      const items = [
        ["轮询模式", status.poll_mode || "-"],
        ["待发队列", String(status.pending_count || 0)],
        ["最近轮询", status.last_poll_at || "-"],
        ["最近发送", status.last_success || "-"],
        ["识别标题", status.last_identified_title || "-"],
        ["最近错误", status.last_error || "-"],
      ];
      metricsEl.innerHTML = items.map(([label, value]) => `<div class="metric"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join("");
    }

    function renderSelected() {
      manualContactEl.value = selected;
      const rules = (state.rules && state.rules.rules) || {};
      const rule = rules[selected] || {};
      document.getElementById("ruleContact").value = selected || "";
      document.getElementById("ruleTarget").value = rule.target || selected || "";
      document.getElementById("ruleAliases").value = Array.isArray(rule.aliases) ? rule.aliases.join(", ") : "";
      document.getElementById("ruleAutoSend").checked = !!rule.auto_send;
      document.getElementById("ruleExactTitle").checked = rule.require_exact_title !== false;
      document.getElementById("ruleNote").value = rule.note || "";
      renderHistory();
    }

    function renderHistory() {
      const items = selected ? history.filter(item => item.contact === selected) : history;
      historyEl.innerHTML = (items.length ? items : history).slice().reverse().map(item => `
        <article class="event">
          <div class="event-top"><strong>${esc(item.contact || "未知")}</strong><span>${esc(item.time || "")} · ${esc(item.status || "")}</span></div>
          <div class="event-text">${esc(item.text || "")}</div>
        </article>
      `).join("") || '<div class="subtle">暂无记录</div>';
    }

    function selectContact(contact) {
      selected = contact;
      renderContacts();
      renderSelected();
      textEl.focus();
    }

    async function refresh() {
      const response = await fetch("/api/state");
      state = await response.json();
      contacts = state.contacts || [];
      history = state.history || [];
      if (!selected && contacts.length) selected = contacts[0];
      renderStatus();
      renderContacts();
      renderSelected();
    }

    document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(item => item.classList.toggle("active", item === tab));
      document.querySelectorAll(".view").forEach(view => view.classList.toggle("active", view.id === tab.dataset.view));
    }));

    async function updateControl(patch) {
      const response = await fetch("/api/control", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(patch)});
      const data = await response.json();
      if (!data.ok) throw new Error(data.error || "控制更新失败");
      await refresh();
    }
    document.getElementById("paused").addEventListener("change", event => updateControl({paused: event.target.checked}));
    document.getElementById("autoSendEnabled").addEventListener("change", event => updateControl({auto_send_enabled: event.target.checked}));
    document.getElementById("manualOnly").addEventListener("change", event => updateControl({manual_only: event.target.checked}));
    document.getElementById("refreshBtn").addEventListener("click", refresh);
    contactSearchEl.addEventListener("input", renderContacts);
    contactSearchEl.addEventListener("keydown", event => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      const contact = contactSearchEl.value.trim();
      if (!contact) return;
      if (!contacts.includes(contact)) contacts.unshift(contact);
      selectContact(contact);
    });

    document.getElementById("sendForm").addEventListener("submit", async event => {
      event.preventDefault();
      const contact = manualContactEl.value.trim() || selected;
      const text = textEl.value.trim();
      if (!contact || !text) {
        sendStatusEl.textContent = "联系人和内容不能为空";
        return;
      }
      sendStatusEl.textContent = "正在调用 Mac 微信";
      try {
        const response = await fetch("/api/send", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({contact, text})
        });
        const data = await response.json();
        if (!data.ok) throw new Error(data.error || "发送失败");
        selected = contact;
        textEl.value = "";
        sendStatusEl.textContent = "已提交";
        await refresh();
      } catch (error) {
        sendStatusEl.textContent = error.message;
      }
    });

    document.getElementById("ruleForm").addEventListener("submit", async event => {
      event.preventDefault();
      const payload = {
        contact: document.getElementById("ruleContact").value.trim(),
        target: document.getElementById("ruleTarget").value.trim(),
        aliases: document.getElementById("ruleAliases").value,
        auto_send: document.getElementById("ruleAutoSend").checked,
        require_exact_title: document.getElementById("ruleExactTitle").checked,
        note: document.getElementById("ruleNote").value.trim(),
      };
      const response = await fetch("/api/rules", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
      const data = await response.json();
      if (!data.ok) {
        alert(data.error || "保存失败");
        return;
      }
      selected = payload.contact;
      await refresh();
    });

    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>"""


class PollNetworkError(RuntimeError):
    pass


def configure_poll_mode(args):
    auto_wait = int(args.worker_wait_ms) < 0
    auto_timeout = int(args.poll_timeout) <= 0
    if auto_wait:
        if worker_supports_wait_ms(args.poll_url):
            args.worker_wait_ms = 8000
            if auto_timeout:
                args.poll_timeout = 12
            update_status(worker_wait_ms=args.worker_wait_ms, poll_timeout=args.poll_timeout, poll_mode="short")
            print("poll: Worker supports waitMs, using short polling waitMs=8000 timeout=12", flush=True)
        else:
            args.worker_wait_ms = 25000
            if auto_timeout:
                args.poll_timeout = 35
            update_status(worker_wait_ms=args.worker_wait_ms, poll_timeout=args.poll_timeout, poll_mode="legacy")
            print("poll: Worker waitMs not deployed yet, using legacy long polling waitMs=25000 timeout=35", flush=True)
    elif auto_timeout:
        args.poll_timeout = max(5, int(args.worker_wait_ms / 1000) + 10)
        update_status(worker_wait_ms=args.worker_wait_ms, poll_timeout=args.poll_timeout, poll_mode="manual")


def worker_supports_wait_ms(poll_url):
    request = urllib.request.Request(with_query_param(poll_url, "waitMs", "0"), headers={"User-Agent": "BarkBridge-MacRelay/1.0"})
    start = time.time()
    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            json.loads(response.read().decode("utf-8"))
        return time.time() - start < 5
    except Exception as exc:
        print(f"poll: waitMs probe failed, keeping legacy mode: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return False


def fetch_replies(poll_url, timeout_seconds=35, worker_wait_ms=25000):
    update_status(last_poll_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    url = with_query_param(poll_url, "waitMs", str(max(0, int(worker_wait_ms))))
    request = urllib.request.Request(url, headers={"User-Agent": "BarkBridge-MacRelay/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=max(3, int(timeout_seconds))) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:300]}") from exc
    except (urllib.error.URLError, TimeoutError, http.client.RemoteDisconnected, ConnectionError) as exc:
        raise PollNetworkError(f"{type(exc).__name__}: {exc}") from exc
    if isinstance(payload, list):
        return payload
    return payload.get("replies") or []


def with_query_param(url, key, value):
    parsed = urllib.parse.urlparse(url)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    pairs = [(k, v) for k, v in pairs if k != key]
    pairs.append((key, value))
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(pairs)))


def process_replies(replies, args):
    if not replies:
        return
    normalized_replies = [normalize_reply(reply) for reply in replies]
    remaining = process_voice_batches([reply for reply in normalized_replies if reply["action"] == "voice_transcribe"], args)
    for normalized in normalized_replies:
        if normalized["action"] == "voice_transcribe":
            continue
        if normalized["source"] == "control" or normalized["action"]:
            handle_remote_control(normalized, args)
            continue
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
        control = load_control()
        if control["paused"] or control["manual_only"] or not control["auto_send_enabled"]:
            stage_manual_review(contact, text, rule["target"])
            reason = control_pause_reason(control)
            append_history(contact, text, f"manual-review: {reason}")
            print(f"manual-review: {contact} -> {rule['target']} ({reason})", flush=True)
            send_receipt(args.receipt_url, "BarkBridge 未自动发送", f"{reason}，已复制内容: {contact} -> {rule['target']}")
            continue
        if is_recently_processed(normalized["id"]):
            print(f"skip already processed: {contact} -> {rule['target']} ({normalized['id']})", flush=True)
            continue
        if not rule["auto_send"]:
            stage_manual_review(contact, text, rule["target"])
            print(f"manual-review: {contact} -> {rule['target']} ({rule['reason']})", flush=True)
            send_receipt(args.receipt_url, "BarkBridge 未自动发送", f"{rule['reason']}，已复制内容，请在 Mac 微信手动确认: {contact} -> {rule['target']}")
            continue
        try:
            with SEND_LOCK:
                result = send_wechat(rule["target"], text, args.send_shortcut, rule)
            remember_processed(normalized["id"], rule["target"], text)
            CONTACT_FAILURES.pop(rule["target"], None)
            update_status(last_reply_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), last_send_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), last_success=f"{contact} -> {rule['target']}", last_identified_title=result["actual_title"], last_error="")
            append_history(contact, text, f"sent: {result['actual_title']}")
            print(f"sent-action: {contact} -> {rule['target']} ({result['actual_title']})", flush=True)
            send_receipt(args.receipt_url, "BarkBridge 已发送", format_receipt(contact, rule["target"], result["actual_title"], text))
        except Exception as exc:
            note_contact_failure(rule["target"])
            normalized["attempts"] = attempts + 1
            normalized["last_error"] = f"{type(exc).__name__}: {exc}"
            stage_manual_review(contact, text, rule["target"])
            append_history(contact, text, f"failed: {normalized['last_error']}")
            update_status(last_error=f"{contact}: {normalized['last_error']}")
            if normalized["attempts"] <= args.max_retries:
                remaining.append(normalized)
                print(f"queued retry {normalized['attempts']}/{args.max_retries}: {contact}", file=sys.stderr, flush=True)
            else:
                print(f"drop after retries: {contact}: {normalized['last_error']}", file=sys.stderr, flush=True)
            send_receipt(
                args.receipt_url,
                "BarkBridge 回复失败",
                format_failure_receipt(contact, rule["target"], normalized["last_error"], normalized["attempts"], args.max_retries),
            )
    save_pending(remaining)


def normalize_reply(reply):
    return {
        "id": str(reply.get("id") or f"local-{int(time.time() * 1000)}"),
        "token": str(reply.get("token") or ""),
        "contact": str(reply.get("contact") or "").strip(),
        "text": str(reply.get("text") or "").strip(),
        "source": str(reply.get("source") or "").strip(),
        "action": str(reply.get("action") or "").strip(),
        "value": reply.get("value"),
        "createdAt": int(reply.get("createdAt") or 0),
        "attempts": int(reply.get("attempts") or 0),
        "last_error": str(reply.get("last_error") or ""),
    }


def handle_voice_transcribe(task, args):
    contact = task["contact"]
    if not contact:
        print(f"skip invalid voice task: {task}", flush=True)
        return
    if not voice_transcribe_enabled(args):
        print(f"voice-transcribe disabled: {contact}", flush=True)
        return
    if is_recently_processed(task["id"]):
        print(f"skip already processed voice task: {contact} ({task['id']})", flush=True)
        return
    handle_voice_transcribe_batch(contact, [task], args)


def process_voice_batches(tasks, args):
    batches = {}
    for task in tasks:
        contact = task["contact"]
        if not contact:
            print(f"skip invalid voice task: {task}", flush=True)
            continue
        if is_expired_voice_task(task, args.voice_task_ttl_minutes):
            reason = f"voice-transcribe-expired: older than {args.voice_task_ttl_minutes} minutes"
            append_history(contact, task["text"], reason)
            remember_processed(task["id"], contact, reason)
            print(f"drop expired voice task: {contact} ({task['id']})", file=sys.stderr, flush=True)
            continue
        if not voice_transcribe_enabled(args):
            print(f"voice-transcribe disabled: {contact}", flush=True)
            append_history(contact, task["text"], "voice-transcribe-disabled")
            remember_processed(task["id"], contact, "voice-transcribe-disabled")
            continue
        if is_recently_processed(task["id"]):
            print(f"skip already processed voice task: {contact} ({task['id']})", flush=True)
            continue
        batches.setdefault(contact, []).append(task)
    remaining = []
    for contact, contact_tasks in batches.items():
        remaining.extend(handle_voice_transcribe_batch(contact, contact_tasks, args))
    return remaining


def handle_voice_transcribe_batch(contact, tasks, args):
    tasks = sorted(tasks, key=lambda item: int(item.get("createdAt") or 0), reverse=True)
    rule = resolve_contact_rule(contact)
    try:
        with SEND_LOCK:
            result = transcribe_recent_voices(rule["target"], rule, len(tasks), args)
        texts = [text.strip() for text in result["texts"] if text.strip()]
        if not texts:
            raise RuntimeError("未识别到微信转出的文字，可能没有点中语音消息或当前 Mac 微信未完成转文字")
        rejected = [text for text in texts if is_non_wechat_transcription(text) or is_low_confidence_transcription(text)]
        for text in rejected:
            print(f"reject voice transcription: {contact}: {text[:120]}", file=sys.stderr, flush=True)
        texts = [text for text in texts if text not in rejected]
        if not texts:
            raise RuntimeError("OCR 结果疑似不是有效微信语音转文字内容，已丢弃并等待重试")
        for index, text in enumerate(texts):
            if index < len(tasks):
                remember_processed(tasks[index]["id"], rule["target"], text)
            append_history(contact, text, f"voice-transcribed: {result['actual_title']}")
            upload_transcription(args, contact, text)
            send_receipt(args.receipt_url, "BarkBridge 语音已转文字", f"{contact}\n{text[:500]}")
        update_status(
            last_reply_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            last_success=f"语音转文字: {contact} x{len(texts)}",
            last_identified_title=result["actual_title"],
            last_error="",
        )
        remaining = retry_voice_tasks(tasks[len(texts):], contact, "visible voice not found", args.voice_max_retries)
        print(f"voice-transcribed: {contact}: {len(texts)}/{len(tasks)}", flush=True)
        return remaining
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        remaining = retry_voice_tasks(tasks, contact, error, args.voice_max_retries)
        update_status(last_error=f"语音转文字失败 {contact}: {error}")
        send_receipt(args.receipt_url, "BarkBridge 语音转文字失败", f"{contact}\n{error}\n请在 Mac 微信手动点语音转文字。")
        print(f"voice-transcribe failed: {contact}: {error}", file=sys.stderr, flush=True)
        return remaining


def retry_voice_tasks(tasks, contact, reason, max_attempts=1):
    remaining = []
    for task in tasks:
        task["attempts"] = int(task.get("attempts") or 0) + 1
        status = f"voice-transcribe-retry: {reason}"
        if task["attempts"] > max_attempts:
            status = f"voice-transcribe-failed: {reason}"
            remember_processed(task.get("id"), contact, status)
        else:
            remaining.append(task)
        append_history(contact, task["text"], status)
    return remaining


def voice_transcribe_enabled(args):
    return bool(getattr(args, "enable_voice_transcribe", False)) and not bool(getattr(args, "disable_voice_transcribe", False))


def is_expired_voice_task(task, ttl_minutes):
    try:
        created_at = int(task.get("createdAt") or 0)
    except Exception:
        created_at = 0
    if created_at <= 0 or ttl_minutes <= 0:
        return False
    return int(time.time() * 1000) - created_at > ttl_minutes * 60 * 1000


def is_recent_duplicate_transcription(contact, text, window_seconds=180):
    now = datetime.datetime.now()
    normalized_text = normalize_match_text(text)
    if not contact or not normalized_text:
        return False
    for item in reversed(load_history()):
        if str(item.get("contact") or "").strip() != contact:
            continue
        if not str(item.get("status") or "").startswith("voice-transcribed"):
            continue
        if normalize_match_text(item.get("text") or "") != normalized_text:
            continue
        try:
            then = datetime.datetime.strptime(str(item.get("time") or ""), "%Y-%m-%d %H:%M:%S")
        except Exception:
            return True
        return (now - then).total_seconds() <= window_seconds
    return False


def handle_remote_control(command, args):
    action = command["action"]
    value = command["value"]
    control = load_control()
    if action == "pause":
        control["paused"] = True
    elif action == "resume":
        control["paused"] = False
    elif action == "auto_send_on":
        control["auto_send_enabled"] = True
    elif action == "auto_send_off":
        control["auto_send_enabled"] = False
    elif action == "manual_only_on":
        control["manual_only"] = True
    elif action == "manual_only_off":
        control["manual_only"] = False
    else:
        print(f"skip unknown control action: {action}", file=sys.stderr, flush=True)
        return
    save_control(control)
    text = f"远程控制已执行: {action}={value}"
    append_history("BarkBridge 控制", text, "control")
    update_status(last_success=text)
    send_receipt(args.receipt_url, "BarkBridge 控制已执行", text)
    print(f"control-action: {text}", flush=True)


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


def save_contact_rules(rules):
    os.makedirs(os.path.dirname(CONTACT_RULES_PATH), exist_ok=True)
    if not isinstance(rules, dict):
        raise ValueError("contact rules root must be an object")
    if not isinstance(rules.get("rules"), dict):
        rules["rules"] = {}
    with open(CONTACT_RULES_PATH, "w", encoding="utf-8") as fh:
        json.dump(rules, fh, ensure_ascii=False, indent=2)


def resolve_contact_rule(contact):
    contact = str(contact or "").strip()
    data = load_contact_rules()
    raw_rule = data.get("rules", {}).get(contact)
    if isinstance(raw_rule, dict):
        target = str(raw_rule.get("target") or contact).strip() or contact
        auto_send = bool(raw_rule.get("auto_send"))
        if target in COMMAND_ADAPTER_TARGETS and not command_adapter_for(target, raw_rule):
            auto_send = False
        return {
            "target": target,
            "auto_send": auto_send,
            "aliases": normalized_aliases(raw_rule),
            "require_exact_title": raw_rule.get("require_exact_title", True) is not False,
            "note": str(raw_rule.get("note") or "").strip(),
            "kind": str(raw_rule.get("kind") or infer_contact_kind(target)).strip(),
            "reason": "未配置专用命令适配器，要求人工确认" if target in COMMAND_ADAPTER_TARGETS and not command_adapter_for(target, raw_rule) else ("联系人规则要求人工确认" if not auto_send else "联系人规则允许自动发送"),
        }
    if is_risky_contact_name(contact):
        return {
            "target": contact,
            "auto_send": False,
            "aliases": [],
            "require_exact_title": True,
            "note": "",
            "kind": infer_contact_kind(contact),
            "reason": "联系人名称过短或不唯一，未配置规则",
        }
    auto_send = bool(data.get("default_auto_send"))
    return {
        "target": contact,
        "auto_send": auto_send,
        "aliases": [],
        "require_exact_title": True,
        "note": "",
        "kind": infer_contact_kind(contact),
        "reason": "默认规则允许自动发送" if auto_send else "默认规则要求人工确认",
    }


def infer_contact_kind(contact):
    contact = str(contact or "")
    if contact in COMMAND_ADAPTER_TARGETS or "bot" in contact.lower():
        return "special"
    if "群" in contact or "、" in contact:
        return "group"
    return "person"


def normalized_aliases(rule):
    aliases = rule.get("aliases", []) if isinstance(rule, dict) else []
    if isinstance(aliases, str):
        aliases = [aliases]
    if not isinstance(aliases, list):
        return []
    return [str(alias).strip() for alias in aliases if str(alias).strip()]


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


def load_processed():
    try:
        with open(PROCESSED_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception as exc:
        print(f"error: failed to load processed replies: {exc}", file=sys.stderr, flush=True)
        return []


def processed_key(reply_id):
    return str(reply_id or "").strip()


def is_recently_processed(reply_id, window_seconds=1800):
    if not reply_id:
        return False
    now = int(time.time())
    key = processed_key(reply_id)
    return any(
        item.get("key") == key and now - int(item.get("time") or 0) <= window_seconds
        for item in load_processed()
        if isinstance(item, dict)
    )


def remember_processed(reply_id, contact, text):
    now = int(time.time())
    items = [
        item for item in load_processed()
        if isinstance(item, dict) and now - int(item.get("time") or 0) <= 86400
    ]
    items.append({"key": processed_key(reply_id), "contact": str(contact), "text": str(text), "time": now})
    os.makedirs(os.path.dirname(PROCESSED_PATH), exist_ok=True)
    with open(PROCESSED_PATH, "w", encoding="utf-8") as fh:
        json.dump(items[-300:], fh, ensure_ascii=False, indent=2)


def send_receipt(receipt_url, title, body):
    if not receipt_url:
        return
    base = receipt_url.rstrip("/")
    url = f"{base}/{urllib.parse.quote(title)}/{urllib.parse.quote(body)}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "BarkBridge-MacRelay/1.0"})
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"receipt sent: HTTP {response.status}: {title}: {body[:120]}", flush=True)
    except Exception as exc:
        print(f"receipt error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)


def format_receipt(source_contact, target_contact, actual_title, text):
    preview = text.replace("\n", " ").strip()
    if len(preview) > 60:
        preview = preview[:57] + "..."
    return f"通知: {source_contact}\n目标: {target_contact}\n识别: {actual_title}\n内容: {preview}"


def format_failure_receipt(source_contact, target_contact, error, attempts, max_retries):
    return (
        f"通知: {source_contact}\n"
        f"目标: {target_contact}\n"
        f"重试: {attempts}/{max_retries}\n"
        f"处理: 已拦截自动发送，内容已复制到手动确认区\n"
        f"原因: {error}"
    )


def send_wechat(contact, text, send_shortcut, rule=None):
    if contact in COMMAND_ADAPTER_TARGETS:
        send_command_adapter(contact, text)
        return {"actual_title": contact}
    bounds = get_wechat_window_bounds()
    select_contact_by_search(contact, bounds)
    actual_title = verify_selected_chat(contact, text, bounds, rule or {})
    click_message_input(bounds)
    paste_and_send(text, send_shortcut)
    return {"actual_title": actual_title}


def transcribe_latest_voice(contact, rule=None):
    result = transcribe_recent_voices(contact, rule, 1)
    if not result["texts"]:
        raise RuntimeError("未识别到微信转出的文字，可能没有点中语音消息或当前 Mac 微信未完成转文字")
    return {"actual_title": result["actual_title"], "text": result["texts"][0]}


def transcribe_recent_voices(contact, rule=None, count=1, args=None):
    bounds = get_wechat_window_bounds()
    select_contact_by_search(contact, bounds)
    actual_title = verify_selected_chat(contact, "语音转文字", bounds, rule or {})
    scroll_chat_to_bottom(bounds)
    before = read_chat_body_text(bounds, ocr_timeout=8)
    texts = []
    used_points = set()
    click_limit = int(getattr(args, "voice_click_limit", 24) or 24)
    menu_limit = int(getattr(args, "voice_menu_limit", 12) or 12)
    probe_timeout = float(getattr(args, "voice_probe_timeout", 0.8) or 0.8)
    final_timeout = float(getattr(args, "voice_final_timeout", 5.0) or 5.0)
    for _ in range(max(1, int(count))):
        text = ""
        if bool(getattr(args, "voice_left_click_first", False)):
            text = click_visible_voice_to_text(bounds, before, used_points, click_limit, probe_timeout)
        if not text:
            try:
                trigger_voice_context_menu(bounds, used_points, menu_limit)
                text = wait_for_transcription(before, bounds, timeout_seconds=final_timeout)
            except Exception:
                text = ""
        if not text:
            break
        texts.append(text)
        before = read_chat_body_text(bounds, ocr_timeout=8)
    return {"actual_title": actual_title, "texts": texts}


def scroll_chat_to_bottom(bounds):
    click_at(bounds["left"] + (bounds["width"] * 0.64), bounds["top"] + (bounds["height"] * 0.55))
    script = r'''
tell application "System Events"
  key code 125 using command down
  delay 0.2
  key code 121
  delay 0.2
end tell
'''
    try:
        subprocess.run([osascript_bin(), "-e", script], check=True, timeout=3)
    except Exception:
        pass


def voice_click_candidates(bounds, limit=24):
    duration_candidates = voice_duration_candidates(bounds)
    if duration_candidates:
        return unique_points(duration_candidates)[:max(1, int(limit))]
    y_offsets = (145, 190)
    chat_left = 280
    chat_right = int(bounds["width"] - 80)
    incoming_x_offsets = list(range(chat_left + 80, min(chat_left + 430, chat_right), 100))
    outgoing_start = max(chat_left + 470, int(bounds["width"] * 0.58))
    outgoing_x_offsets = list(range(outgoing_start, chat_right, 150))
    x_offsets = incoming_x_offsets + outgoing_x_offsets
    candidates = []
    for y_offset in y_offsets:
        for x_offset in x_offsets:
            candidates.append((bounds["left"] + x_offset, bounds["top"] + bounds["height"] - y_offset))
    return unique_points(candidates)[:max(1, int(limit))]


def voice_duration_candidates(bounds):
    boxes = read_chat_body_boxes(bounds)
    rows = []
    for item in boxes:
        text = str(item.get("text") or "").strip()
        if not is_voice_duration_text(text):
            continue
        cx = bounds["left"] + item["cropX"] + item["x"] + (item["width"] / 2)
        cy = bounds["top"] + item["cropY"] + item["y"] + (item["height"] / 2)
        if cy < bounds["top"] + bounds["height"] * 0.45:
            continue
        rows.append({"text": text, "cx": cx, "cy": cy})
    rows.sort(key=lambda row: row["cy"], reverse=True)
    candidates = []
    for row in rows[:4]:
        cx = row["cx"]
        cy = row["cy"]
        print(f"voice duration OCR: {row['text']} at {round(cx)},{round(cy)}", flush=True)
        for dx in (-115, -80, -45, -10, 30, 65):
            candidates.append((cx + dx, cy))
        for dx in (-90, -50, -10, 35):
            candidates.append((cx + dx, cy + 16))
            candidates.append((cx + dx, cy - 16))
    if candidates:
        print(f"voice duration OCR candidates: {len(candidates)}", flush=True)
    return unique_points(candidates)


def is_voice_duration_text(text):
    compact = normalize_match_text(text)
    return bool(re.fullmatch(r"[0-9]{1,2}[\"”″秒]?", compact) or re.fullmatch(r"[0-9]{1,2}s", compact))


def unique_points(points):
    seen = set()
    unique = []
    for x, y in points:
        key = (round(x), round(y))
        if key in seen:
            continue
        seen.add(key)
        unique.append((x, y))
    return unique


def click_visible_voice_to_text(bounds, before_lines, used_points=None, limit=24, probe_timeout=0.8):
    used_points = used_points if used_points is not None else set()
    candidates = voice_click_candidates(bounds, limit)
    print(f"voice click scan: {len(candidates)} candidates", flush=True)
    for x, y in candidates:
        point_key = (round(x), round(y))
        if point_key in used_points:
            continue
        used_points.add(point_key)
        click_at(x, y)
        text = wait_for_transcription(before_lines, bounds, timeout_seconds=probe_timeout)
        if text:
            return text
    return ""


def trigger_voice_context_menu(bounds, used_points=None, limit=12):
    used_points = used_points if used_points is not None else set()
    duration_points = voice_click_candidates(bounds, limit)
    if duration_points:
        candidates = duration_points
    else:
        candidates = []
        chat_left = 280
        chat_right = int(bounds["width"] - 80)
        for y_offset in (145, 190):
            for x_offset in range(chat_left + 90, min(chat_left + 450, chat_right), 120):
                candidates.append((bounds["left"] + x_offset, bounds["top"] + bounds["height"] - y_offset))
        candidates = unique_points(candidates)[:max(1, int(limit))]
    print(f"voice menu scan: {len(candidates)} candidates", flush=True)
    last_error = None
    for x, y in candidates:
        point_key = (round(x), round(y))
        if point_key in used_points:
            continue
        used_points.add(point_key)
        try:
            right_click_at(x, y)
            if click_voice_to_text_menu_item():
                return
        except Exception as exc:
            last_error = exc
    if last_error:
        raise RuntimeError(f"无法打开语音转文字菜单: {last_error}") from last_error
    raise RuntimeError("没有找到微信语音转文字菜单项")


def trigger_voice_context_menu_legacy(bounds, used_points=None):
    used_points = used_points if used_points is not None else set()
    chat_left = 280
    chat_right = int(bounds["width"] - 80)
    incoming_x_offsets = list(range(chat_left + 45, min(chat_left + 500, chat_right), 56))
    outgoing_start = max(chat_left + 470, int(bounds["width"] * 0.58))
    x_offsets = incoming_x_offsets + list(range(outgoing_start, chat_right, 110))
    y_offsets = (145, 190, 240, 295, 350)
    last_error = None
    print(f"voice menu scan: {len(x_offsets) * len(y_offsets)} candidates", flush=True)
    for y_offset in y_offsets:
        for x_offset in x_offsets:
            x = bounds["left"] + min(x_offset, max(300, bounds["width"] * 0.45))
            y = bounds["top"] + bounds["height"] - y_offset
            point_key = (round(x), round(y))
            if point_key in used_points:
                continue
            used_points.add(point_key)
            try:
                right_click_at(x, y)
                if click_voice_to_text_menu_item():
                    return
            except Exception as exc:
                last_error = exc
    if last_error:
        raise RuntimeError(f"无法打开语音转文字菜单: {last_error}") from last_error
    raise RuntimeError("没有找到微信语音转文字菜单项")


def wait_for_transcription(before_lines, bounds, timeout_seconds):
    deadline = time.time() + max(1, timeout_seconds)
    while time.time() < deadline:
        time.sleep(0.8)
        after = read_chat_body_text(bounds, ocr_timeout=6)
        text = extract_transcription(before_lines, after)
        if text:
            return text
    return ""


def click_voice_to_text_menu_item():
    script = r'''
on run argv
  tell application "System Events"
    tell process "WeChat"
      set menuNames to {"转文字", "转换为文字", "语音转文字", "Convert to Text", "Speech to Text"}
      repeat 15 times
        repeat with candidateMenu in menus
          repeat with targetName in menuNames
            try
              click menu item (targetName as text) of candidateMenu
              return "ok"
            end try
          end repeat
          try
            repeat with itemRef in menu items of candidateMenu
              set itemTitle to name of itemRef
              if itemTitle contains "转文字" or itemTitle contains "转换为文字" or itemTitle contains "语音转文字" then
                click itemRef
                return "ok"
              end if
            end repeat
          end try
        end repeat
        delay 0.1
      end repeat
    end tell
    key code 53
  end tell
  return "missing"
end run
'''
    result = subprocess.run([osascript_bin(), "-e", script], check=True, capture_output=True, text=True, timeout=5)
    return result.stdout.strip() == "ok"


def read_chat_body_text(bounds, ocr_timeout=20):
    ensure_ocr_helper()
    ensure_wechat_frontmost()
    crop = chat_body_crop(bounds)
    fd, path = tempfile.mkstemp(prefix="barkbridge-chat-", suffix=".png")
    os.close(fd)
    try:
        region = f"{int(crop['x'])},{int(crop['y'])},{int(crop['width'])},{int(crop['height'])}"
        subprocess.run(["/usr/sbin/screencapture", "-x", "-R", region, path], check=True, timeout=5)
        result = subprocess.run([OCR_HELPER_BIN, path], check=True, capture_output=True, text=True, timeout=max(2, ocr_timeout))
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def read_chat_body_boxes(bounds):
    ensure_ocr_boxes_helper()
    ensure_wechat_frontmost()
    crop = chat_body_crop(bounds)
    fd, path = tempfile.mkstemp(prefix="barkbridge-chat-boxes-", suffix=".png")
    os.close(fd)
    try:
        region = f"{int(crop['x'])},{int(crop['y'])},{int(crop['width'])},{int(crop['height'])}"
        subprocess.run(["/usr/sbin/screencapture", "-x", "-R", region, path], check=True, timeout=5)
        result = subprocess.run([OCR_BOXES_HELPER_BIN, path], check=True, capture_output=True, text=True, timeout=20)
        rows = json.loads(result.stdout or "[]")
        for row in rows:
            row["cropX"] = crop["x"] - bounds["left"]
            row["cropY"] = crop["y"] - bounds["top"]
        return rows
    except Exception as exc:
        print(f"voice duration OCR failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return []
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def chat_body_crop(bounds):
    return {
        "x": bounds["left"] + 250,
        "y": bounds["top"] + 55,
        "width": max(420, bounds["width"] - 300),
        "height": max(300, bounds["height"] - 185),
    }


def ensure_wechat_frontmost():
    script = r'''
tell application "WeChat"
  activate
  try
    reopen
  end try
end tell
delay 0.8
tell application "System Events"
  try
    set frontmost of process "WeChat" to true
  end try
  delay 0.4
  set frontApp to name of first application process whose frontmost is true
end tell
return frontApp
'''
    result = subprocess.run([osascript_bin(), "-e", script], check=True, capture_output=True, text=True, timeout=5)
    front_app = result.stdout.strip()
    if front_app not in {"WeChat", "微信"}:
        raise RuntimeError(f"微信窗口未在前台，当前前台为 {front_app or '未知'}，已跳过 OCR 防止误读")


def extract_transcription(before_lines, after_lines):
    before = {normalize_match_text(line) for line in before_lines}
    added = [
        sanitize_transcription_line(line) for line in after_lines
        if is_transcription_line(line) and normalize_match_text(line) not in before
    ]
    if added:
        return "\n".join(tail_transcription_lines(added)).strip()
    return ""


def tail_transcription_lines(lines, max_lines=4):
    picked = []
    for line in reversed([line for line in lines if line.strip()]):
        if is_ocr_noise_line(line):
            if picked:
                break
            continue
        picked.append(line)
        if len(picked) >= max_lines:
            break
    return list(reversed(picked))


def sanitize_transcription_line(text):
    text = str(text or "").strip()
    text = re.sub(r"^[0-9oO小少\"'”“’‘、,，.。:：;；()（）\\s]+", "", text)
    text = re.sub(r"([。！？?])[,，.。]+$", r"\1", text)
    return text.strip()


def is_transcription_line(text):
    text = str(text or "").strip()
    if is_wechat_ui_text(text):
        return False
    if is_ocr_noise_line(text):
        return False
    compact = normalize_match_text(text)
    if len(compact) < 3:
        return False
    if re.fullmatch(r"[0-9oO小少]+[\"'”“’‘、,，.。:：;；()（）\\s]*", text):
        return False
    if not re.search(r"[\u4e00-\u9fffA-Za-z]", text):
        return False
    if re.fullmatch(r"[\W_0-9A-Za-z]{1,8}", text):
        return False
    return True


def is_ocr_noise_line(text):
    text = str(text or "").strip()
    if not text:
        return True
    compact = normalize_match_text(text)
    if re.search(r"[*#@$%^_=+<>|{}\\[\\]~`]", text):
        return True
    digit_count = len(re.findall(r"\d", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    visible_count = max(1, len(re.sub(r"\s", "", text)))
    if digit_count >= 4 and digit_count / visible_count >= 0.18:
        return True
    if cjk_count >= 4 and latin_count >= 1 and not re.search(r"\b(OK|ok|App|Mac|iPhone|Bark|HTTP)\b", text):
        return True
    if len(compact) <= 4 and re.search(r"[!！?？]", text):
        return True
    return False


def is_non_wechat_transcription(text):
    compact = normalize_match_text(text)
    blocked = [
        "barkbridge-release",
        "mac-wechat-relay",
        "本地待处理队列",
        "已编辑",
        "github",
        "codex",
        "queuecount",
        "语音会明确失败或重试",
    ]
    return any(normalize_match_text(item) in compact for item in blocked)


def is_low_confidence_transcription(text):
    text = str(text or "").strip()
    compact = normalize_match_text(text)
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    digit_count = len(re.findall(r"\d", text))
    if len(compact) <= 2:
        return True
    if cjk_count <= 1 and latin_count == 0:
        return True
    if cjk_count <= 2 and re.fullmatch(r"[\u4e00-\u9fff.。…\\s]+", text):
        return True
    if cjk_count <= 2 and digit_count > 0:
        return True
    if compact in {"房", "房.", "房..", "房…", "房....", "白山"}:
        return True
    return False


def is_wechat_ui_text(text):
    compact = normalize_match_text(text)
    if not compact:
        return True
    ui_words = [
        "发送", "聊天", "通讯录", "收藏", "搜索", "微信", "文件传输助手",
        "按住说话", "输入", "表情", "截图", "更多", "转文字",
        "逐条转发", "合并转发", "保存至电脑", "删除", "复制", "翻译",
    ]
    return any(normalize_match_text(word) == compact for word in ui_words)


def upload_transcription(args, contact, text):
    ingest_url = args.ingest_url.strip() or ingest_url_from_poll(args.poll_url)
    if not ingest_url:
        raise RuntimeError("缺少 ingest URL，无法回写语音转文字结果")
    secret = query_param(args.poll_url, "secret")
    if not secret:
        raise RuntimeError("poll URL 缺少 secret，无法回写语音转文字结果")
    payload = {
        "secret": secret,
        "contact": contact,
        "text": f"语音转文字：\n{text}",
        "direction": "incoming",
        "source": "mac_voice_transcribe",
        "mediaType": "voice_text",
        "createdAt": int(time.time() * 1000),
    }
    request = urllib.request.Request(
        ingest_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "BarkBridge-MacRelay/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8", errors="replace")
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"ingest HTTP {response.status}: {body[:200]}")


def ingest_url_from_poll(poll_url):
    parsed = urllib.parse.urlparse(poll_url)
    return urllib.parse.urlunparse(parsed._replace(path="/ingest", query="", params="", fragment=""))


def query_param(url, name):
    parsed = urllib.parse.urlparse(url)
    return dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)).get(name, "")


def command_adapter_for(contact, rule=None):
    env_name = f"BARKBRIDGE_{contact.upper()}_COMMAND"
    env_command = os.environ.get(env_name)
    if env_command:
        return env_command
    if contact == "微信ClawBot":
        env_command = os.environ.get("BARKBRIDGE_CLAWBOT_COMMAND")
        if env_command:
            return env_command
    if isinstance(rule, dict):
        command = str(rule.get("command") or "").strip()
        if command:
            return command
    return ""


def send_command_adapter(contact, text):
    command = command_adapter_for(contact, load_contact_rules().get("rules", {}).get(contact))
    if not command:
        stage_manual_review(contact, text, contact)
        raise RuntimeError(f"{contact} 未配置专用命令适配器，已复制内容，未自动发送")
    args = [
        part.replace("{contact}", contact).replace("{text}", text)
        for part in shlex.split(command)
    ]
    if "{text}" not in command:
        args.append(text)
    subprocess.run(args, check=True, timeout=60)


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
      key code 53
      delay 0.2
      set mainWindow to missing value
      repeat with candidateWindow in windows
        if name of candidateWindow is "微信" then
          set mainWindow to candidateWindow
          exit repeat
        end if
      end repeat
      if mainWindow is missing value then
        set mainWindow to window 1
      end if
      try
        set value of attribute "AXMinimized" of mainWindow to false
      end try
      try
        perform action "AXRaise" of mainWindow
      end try
      try
        set position of mainWindow to {0, 0}
        set size of mainWindow to {1440, 900}
      end try
      delay 0.2

      set windowPosition to position of mainWindow
      set windowLeft to item 1 of windowPosition
      set windowTop to item 2 of windowPosition
      set windowSize to size of mainWindow
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


def ensure_ocr_helper():
    if os.path.exists(OCR_HELPER_BIN) and os.path.getmtime(OCR_HELPER_BIN) >= os.path.getmtime(OCR_HELPER_SOURCE):
        return
    subprocess.run(["/usr/bin/swiftc", OCR_HELPER_SOURCE, "-o", OCR_HELPER_BIN], check=True, timeout=30)


def ensure_ocr_boxes_helper():
    if os.path.exists(OCR_BOXES_HELPER_BIN) and os.path.getmtime(OCR_BOXES_HELPER_BIN) >= os.path.getmtime(OCR_BOXES_HELPER_SOURCE):
        return
    subprocess.run(["/usr/bin/swiftc", OCR_BOXES_HELPER_SOURCE, "-o", OCR_BOXES_HELPER_BIN], check=True, timeout=30)


def click_at(x, y):
    ensure_click_helper()
    subprocess.run([CLICK_HELPER_BIN, str(int(x)), str(int(y))], check=True, timeout=5)


def right_click_at(x, y):
    ensure_click_helper()
    subprocess.run([CLICK_HELPER_BIN, str(int(x)), str(int(y)), "right"], check=True, timeout=5)


def select_contact_by_search(contact, bounds):
    script = r'''
on run argv
  set contactName to item 1 of argv
  tell application "System Events"
    tell process "WeChat"
      click menu item "聊天" of menu 1 of menu bar item "窗口" of menu bar 1
      delay 0.3
      click menu item "搜索" of menu 1 of menu bar item "编辑" of menu bar 1
    end tell
    delay 0.2
    set the clipboard to contactName
    keystroke "a" using command down
    delay 0.1
    keystroke "v" using command down
    delay 0.5
    key code 36
  end tell
end run
'''
    subprocess.run([osascript_bin(), "-e", script, contact], check=True, timeout=10)
    time.sleep(0.9)


def verify_selected_chat(expected_contact, text, bounds, rule):
    require_exact_title = rule.get("require_exact_title", True) is not False
    title = read_selected_chat_title(bounds)
    candidates = [expected_contact] + list(rule.get("aliases") or [])
    if title_matches(title, candidates):
        return title
    if not require_exact_title:
        print(f"warn: chat title mismatch ignored: expected={expected_contact!r}, actual={title!r}", file=sys.stderr, flush=True)
        return title or "未识别"
    stage_manual_review(expected_contact, text, expected_contact)
    expected = " / ".join(candidates)
    raise RuntimeError(f"发送前校验失败，目标应为 [{expected}]，实际识别为 [{title or '未识别'}]，已拦截未发送")


def read_selected_chat_title(bounds):
    ensure_ocr_helper()
    ensure_wechat_frontmost()
    crop = {
        "x": bounds["left"] + 215,
        "y": bounds["top"] + 10,
        "width": min(650, max(360, bounds["width"] - 520)),
        "height": 40,
    }
    fd, path = tempfile.mkstemp(prefix="barkbridge-title-", suffix=".png")
    os.close(fd)
    try:
        region = f"{int(crop['x'])},{int(crop['y'])},{int(crop['width'])},{int(crop['height'])}"
        subprocess.run(["/usr/sbin/screencapture", "-x", "-R", region, path], check=True, timeout=5)
        result = subprocess.run([OCR_HELPER_BIN, path], check=True, capture_output=True, text=True, timeout=15)
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        title = " ".join(lines)
        update_status(last_identified_title=title or "未识别")
        return title
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def title_matches(title, candidates):
    normalized_title = normalize_match_text(title)
    if not normalized_title:
        return False
    for candidate in candidates:
        normalized_candidate = normalize_match_text(candidate)
        if normalized_candidate and normalized_candidate in normalized_title:
            return True
    return False


def normalize_match_text(value):
    return "".join(ch for ch in str(value or "").strip().lower() if not ch.isspace())


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
    verify_input_cleared_after_send(text)


def verify_input_cleared_after_send(sent_text):
    script = r'''
on run argv
  set expectedText to item 1 of argv
  try
    set previousClipboard to the clipboard as text
  on error
    set previousClipboard to ""
  end try

  tell application "System Events"
    delay 0.5
    keystroke "a" using command down
    delay 0.1
    keystroke "c" using command down
    delay 0.2
  end tell

  try
    set currentText to the clipboard as text
  on error
    set currentText to ""
  end try
  set the clipboard to previousClipboard

  if currentText is expectedText then
    error "发送后输入框仍保留原内容，微信可能没有发出"
  end if
  if currentText is not "" then
    set compactText to currentText
    set compactText to do shell script "/bin/echo -n " & quoted form of compactText & " | /usr/bin/tr -d '[:space:]'"
    if compactText is "" then
      tell application "System Events"
        key code 51
        delay 0.1
      end tell
    end if
  end if
end run
'''
    subprocess.run([osascript_bin(), "-e", script, sent_text], check=True, timeout=10)


if __name__ == "__main__":
    main()
