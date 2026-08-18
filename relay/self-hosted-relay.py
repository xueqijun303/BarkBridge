#!/usr/bin/env python3
import argparse
import cgi
import html
import io
import json
import os
import queue
import sqlite3
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


DEFAULT_CONTACTS = [
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
    "文件传输助手",
]

HIDDEN_CONTACTS = {
    "BarkBridge配置测试",
    "BarkBridge手机自测",
    "阿里云部署测试",
    "Codex上传复测",
    "本地测试",
}
HIDDEN_CONTACT_PREFIXES = ("BarkBridge", "Codex", "阿里云部署测试", "本地测试")
DEFAULT_CONFIG = {
    "pinnedContacts": ["XQJ家庭群", "幸福一家人", "薛启军工作号"],
    "hiddenContacts": sorted(HIDDEN_CONTACTS),
}
HISTORY_RETAIN_PER_CONTACT = 100
HISTORY_RETAIN_TOTAL = 5000


def is_hidden_contact(contact):
    name = (contact or "").strip()
    return bool(name and (name in HIDDEN_CONTACTS or name.startswith(HIDDEN_CONTACT_PREFIXES)))


def normalize_contact_list(value):
    if isinstance(value, str):
        items = value.replace("\r", "\n").replace(",", "\n").replace("，", "\n").split("\n")
    elif isinstance(value, list):
        items = value
    else:
        items = []
    normalized = []
    for item in items:
        contact = str(item or "").strip()
        if contact and contact not in normalized:
            normalized.append(contact)
    return normalized


class RelayStore:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        self.waiters = []
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.init_db()

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def init_db(self):
        with self.connect() as db:
            db.execute(
                """
                create table if not exists history (
                    id text primary key,
                    contact text not null default '',
                    text text not null default '',
                    source text not null default '',
                    direction text not null default '',
                    status text not null default '',
                    created_at integer not null
                )
                """
            )
            db.execute(
                """
                create table if not exists queue (
                    id text primary key,
                    token text not null default '',
                    contact text not null default '',
                    text text not null default '',
                    source text not null default '',
                    action text not null default '',
                    value text not null default '',
                    direction text not null default '',
                    status text not null default '',
                    created_at integer not null
                )
                """
            )
            db.execute(
                """
                create table if not exists config (
                    key text primary key,
                    value text not null default ''
                )
                """
            )

    def add_history(self, item):
        with self.lock, self.connect() as db:
            db.execute(
                """
                insert or replace into history
                (id, contact, text, source, direction, status, created_at)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item.get("contact", ""),
                    item.get("text", ""),
                    item.get("source", ""),
                    item.get("direction", ""),
                    item.get("status", ""),
                    int(item.get("createdAt") or now_ms()),
                ),
            )
            contact = str(item.get("contact", "")).strip()
            if contact:
                rows = db.execute(
                    "select id from history where contact = ? order by created_at desc limit -1 offset ?",
                    (contact, HISTORY_RETAIN_PER_CONTACT),
                ).fetchall()
                if rows:
                    db.executemany("delete from history where id = ?", rows)
            rows = db.execute("select id from history order by created_at desc limit -1 offset ?", (HISTORY_RETAIN_TOTAL,)).fetchall()
            if rows:
                db.executemany("delete from history where id = ?", rows)

    def enqueue(self, item):
        self.add_history(item)
        with self.lock:
            waiter = self.waiters.pop(0) if self.waiters else None
            if waiter:
                waiter.put(item)
                return
            with self.connect() as db:
                db.execute(
                    """
                    insert or replace into queue
                    (id, token, contact, text, source, action, value, direction, status, created_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["id"],
                        item.get("token", ""),
                        item.get("contact", ""),
                        item.get("text", ""),
                        item.get("source", ""),
                        item.get("action", ""),
                        str(item.get("value", "")),
                        item.get("direction", ""),
                        item.get("status", ""),
                        int(item.get("createdAt") or now_ms()),
                    ),
                )

    def dequeue(self, wait_ms):
        with self.lock:
            items = self.pop_queue_locked()
            if items or wait_ms <= 0:
                return items
            waiter = queue.Queue(maxsize=1)
            self.waiters.append(waiter)
        try:
            return [waiter.get(timeout=wait_ms / 1000)]
        except queue.Empty:
            with self.lock:
                if waiter in self.waiters:
                    self.waiters.remove(waiter)
            return []

    def pop_queue_locked(self):
        with self.connect() as db:
            rows = db.execute(
                "select id, token, contact, text, source, action, value, created_at from queue order by created_at asc limit 200"
            ).fetchall()
            if not rows:
                return []
            db.executemany("delete from queue where id = ?", [(row[0],) for row in rows])
        return [
            {
                "id": row[0],
                "token": row[1],
                "contact": row[2],
                "text": row[3],
                "source": row[4],
                "action": row[5],
                "value": parse_value(row[6]),
                "createdAt": row[7],
            }
            for row in rows
        ]

    def history(self, limit=120):
        with self.connect() as db:
            rows = db.execute(
                "select id, contact, text, source, direction, status, created_at from history order by created_at desc limit ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": row[0],
                "contact": row[1],
                "text": row[2],
                "source": row[3],
                "direction": row[4],
                "status": row[5],
                "createdAt": row[6],
            }
            for row in rows
        ]

    def delete_history_for_contact(self, contact):
        with self.lock, self.connect() as db:
            cursor = db.execute("delete from history where contact = ?", (contact,))
            return cursor.rowcount

    def queue_count(self):
        with self.connect() as db:
            row = db.execute("select count(*) from queue").fetchone()
        return int(row[0] if row else 0)

    def latest_history_time(self, source=None):
        sql = "select max(created_at) from history"
        args = ()
        if source:
            sql += " where source = ?"
            args = (source,)
        with self.connect() as db:
            row = db.execute(sql, args).fetchone()
        return int(row[0] or 0) if row else 0

    def set_meta(self, key, value):
        with self.lock, self.connect() as db:
            db.execute(
                "insert or replace into config (key, value) values (?, ?)",
                (f"meta:{key}", json.dumps(value, ensure_ascii=False)),
            )

    def get_meta(self, key, default=None):
        with self.connect() as db:
            row = db.execute("select value from config where key = ?", (f"meta:{key}",)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except Exception:
            return row[0]

    def status(self):
        return {
            "ok": True,
            "time": now_ms(),
            "queueCount": self.queue_count(),
            "contactCount": len(self.contacts()),
            "historyLimitPerContact": HISTORY_RETAIN_PER_CONTACT,
            "historyLimitTotal": HISTORY_RETAIN_TOTAL,
            "androidLastUploadAt": self.latest_history_time("android"),
            "outgoingLastQueuedAt": self.latest_history_time("compose") or self.latest_history_time("reply"),
            "macLastPollAt": int(self.get_meta("macLastPollAt", 0) or 0),
        }

    def config(self):
        with self.connect() as db:
            rows = db.execute("select key, value from config").fetchall()
        values = dict(DEFAULT_CONFIG)
        for key, value in rows:
            try:
                parsed = json.loads(value)
            except Exception:
                parsed = value
            if key in values:
                values[key] = parsed
        values["pinnedContacts"] = normalize_contact_list(values.get("pinnedContacts"))
        values["hiddenContacts"] = normalize_contact_list(values.get("hiddenContacts"))
        return values

    def save_config(self, data):
        values = {
            "pinnedContacts": normalize_contact_list(data.get("pinnedContacts")),
            "hiddenContacts": normalize_contact_list(data.get("hiddenContacts")),
        }
        with self.lock, self.connect() as db:
            db.executemany(
                "insert or replace into config (key, value) values (?, ?)",
                [(key, json.dumps(value, ensure_ascii=False)) for key, value in values.items()],
            )
        return self.config()

    def contacts(self):
        config = self.config()
        hidden = set(config.get("hiddenContacts", []))
        with self.connect() as db:
            rows = db.execute(
                "select distinct contact from history where contact <> '' order by created_at desc limit 80"
            ).fetchall()
        contacts = []
        for contact in config.get("pinnedContacts", []) + [row[0] for row in rows] + DEFAULT_CONTACTS:
            if contact and contact not in contacts and contact not in hidden and not is_hidden_contact(contact):
                contacts.append(contact)
        return contacts


def parse_value(value):
    if value == "True":
        return True
    if value == "False":
        return False
    return value


def now_ms():
    return int(time.time() * 1000)


def make_id():
    return f"{now_ms()}-{os.urandom(8).hex()}"


def direction_from_source(source):
    if source == "android":
        return "incoming"
    if source in ("reply", "compose"):
        return "outgoing"
    return "system"


def status_from_source(source):
    if source == "android":
        return "received"
    if source in ("reply", "compose"):
        return "queued"
    return "event"


class RelayHandler(BaseHTTPRequestHandler):
    server_version = "BarkBridgeRelay/1.0"

    def do_HEAD(self):
        if self.path_only() in {"/", "/reply", "/compose", "/control", "/chat", "/settings", "/health", "/api/status"}:
            self.send_response(200)
            content_type = "application/json; charset=utf-8" if self.path_only() == "/health" else "text/html; charset=utf-8"
            self.send_header("Content-Type", content_type)
            self.end_headers()
        else:
            self.send_error(404)

    def do_GET(self):
        path = self.path_only()
        query = self.query()
        if path == "/health":
            self.json(self.server.store.status())
        elif path == "/":
            self.html(home_page())
        elif path == "/reply":
            self.html(reply_page(query))
        elif path == "/compose":
            if not self.allowed(query.get("secret", [""])[0]):
                self.html(error_page("密钥不正确", "请使用带 secret 参数的 BarkBridge 主动发送页面。"), 403)
            else:
                self.html(compose_page(query.get("secret", [""])[0], query.get("contact", ["文件传输助手"])[0]))
        elif path == "/control":
            if not self.allowed(query.get("secret", [""])[0]):
                self.html(error_page("密钥不正确", "请使用带 secret 参数的 BarkBridge 控制页面。"), 403)
            else:
                self.html(control_page(query.get("secret", [""])[0]))
        elif path == "/settings":
            if not self.allowed(query.get("secret", [""])[0]):
                self.html(error_page("密钥不正确", "请使用带 secret 参数的 BarkBridge 设置页面。"), 403)
            else:
                self.html(settings_page(query.get("secret", [""])[0]))
        elif path == "/chat":
            if not self.allowed(query.get("secret", [""])[0]):
                self.html(error_page("密钥不正确", "请使用带 secret 参数的 BarkBridge 聊天面板。"), 403)
            else:
                self.html(chat_page(query.get("secret", [""])[0], query.get("contact", [""])[0]))
        elif path == "/api/chat":
            if not self.allowed(query.get("secret", [""])[0]):
                self.json({"history": []}, 403)
            else:
                contact = query.get("contact", [""])[0].strip()
                history = self.server.store.history()
                if contact:
                    visible_history = [item for item in history if item["contact"] == contact]
                else:
                    visible_history = [item for item in history if not is_hidden_contact(item.get("contact", ""))]
                self.json({"history": visible_history})
        elif path == "/api/history":
            if not self.allowed(query.get("secret", [""])[0]):
                self.json({"history": []}, 403)
            else:
                self.json({"history": self.server.store.history()})
        elif path == "/api/contacts":
            if not self.allowed(query.get("secret", [""])[0]):
                self.json({"contacts": []}, 403)
            else:
                self.json({"contacts": self.server.store.contacts(), "config": self.server.store.config()})
        elif path == "/api/config":
            if not self.allowed(query.get("secret", [""])[0]):
                self.json({"config": {}}, 403)
            else:
                self.json({"config": self.server.store.config(), "contacts": self.server.store.contacts()})
        elif path == "/api/status":
            if not self.allowed(query.get("secret", [""])[0]):
                self.json({"ok": False, "error": "密钥不正确"}, 403)
            else:
                self.json(self.server.store.status())
        elif path == "/poll":
            if not self.allowed(query.get("secret", [""])[0]):
                self.json({"replies": []}, 403)
            else:
                self.server.store.set_meta("macLastPollAt", now_ms())
                wait_ms = int(query.get("waitMs", ["25000"])[0] or "25000")
                wait_ms = max(0, min(25000, wait_ms))
                self.json({"replies": self.server.store.dequeue(wait_ms)})
        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path_only()
        if path == "/ingest":
            self.save_incoming()
        elif path == "/reply":
            self.save_reply()
        elif path == "/send":
            self.save_manual()
        elif path == "/control":
            self.save_control()
        elif path == "/api/config":
            self.save_config()
        elif path == "/api/chat/clear":
            self.clear_contact_history()
        else:
            self.send_error(404)

    def save_incoming(self):
        data = self.read_json()
        if not self.allowed(str(data.get("secret", ""))):
            self.json({"ok": False, "error": "密钥不正确"}, 403)
            return
        contact = str(data.get("contact", "")).strip()
        text = str(data.get("text", "")).strip()
        if not contact or not text:
            self.json({"ok": False, "error": "联系人和内容不能为空"}, 400)
            return
        self.server.store.add_history(
            {
                "id": make_id(),
                "contact": contact,
                "text": text,
                "source": "android",
                "direction": "incoming",
                "status": "received",
                "createdAt": int(data.get("createdAt") or now_ms()),
            }
        )
        self.json({"ok": True})

    def save_reply(self):
        data = self.read_form()
        token = str(data.get("token", "")).strip()
        contact = str(data.get("contact", "")).strip()
        text = str(data.get("text", "")).strip()
        if not token:
            self.html(error_page("缺少回复令牌", "请从 BarkBridge 推送通知里的回复链接打开。"), 400)
            return
        if not text:
            self.html(error_page("缺少回复内容", "请输入要发送给微信联系人的回复内容。"), 400)
            return
        self.enqueue(contact, text, "reply", token)
        self.html(simple_page("Reply saved", "Reply saved", "You can close this page."))

    def save_manual(self):
        data = self.read_json_or_form()
        if not self.allowed(str(data.get("secret", ""))):
            self.json({"ok": False, "error": "密钥不正确"}, 403)
            return
        contact = str(data.get("contact", "")).strip()
        text = str(data.get("text", "")).strip()
        if not contact or not text:
            self.json({"ok": False, "error": "联系人和内容不能为空"}, 400)
            return
        self.enqueue(contact, text, "compose", "manual")
        self.json({"ok": True})

    def save_control(self):
        data = self.read_json_or_form()
        if not self.allowed(str(data.get("secret", ""))):
            self.json({"ok": False, "error": "密钥不正确"}, 403)
            return
        action = str(data.get("action", "")).strip()
        if action not in {"pause", "resume", "auto_send_on", "auto_send_off", "manual_only_on", "manual_only_off"}:
            self.json({"ok": False, "error": "未知控制指令"}, 400)
            return
        value = action.endswith("_on") or action == "pause"
        item = {
            "id": make_id(),
            "token": "control",
            "contact": "",
            "text": f"{action}={str(value).lower()}",
            "source": "control",
            "action": action,
            "value": value,
            "direction": "system",
            "status": "event",
            "createdAt": now_ms(),
        }
        self.server.store.enqueue(item)
        self.json({"ok": True})

    def save_config(self):
        data = self.read_json_or_form()
        if not self.allowed(str(data.get("secret", ""))):
            self.json({"ok": False, "error": "密钥不正确"}, 403)
            return
        config = self.server.store.save_config(data)
        self.json({"ok": True, "config": config, "contacts": self.server.store.contacts()})

    def clear_contact_history(self):
        data = self.read_json_or_form()
        if not self.allowed(str(data.get("secret", ""))):
            self.json({"ok": False, "error": "密钥不正确"}, 403)
            return
        contact = str(data.get("contact", "")).strip()
        if not contact:
            self.json({"ok": False, "error": "联系人不能为空"}, 400)
            return
        deleted = self.server.store.delete_history_for_contact(contact)
        self.json({"ok": True, "deleted": deleted, "contact": contact})

    def enqueue(self, contact, text, source, token):
        item = {
            "id": make_id(),
            "token": token,
            "contact": contact,
            "text": text,
            "source": source,
            "direction": direction_from_source(source),
            "status": status_from_source(source),
            "createdAt": now_ms(),
        }
        self.server.store.enqueue(item)

    def allowed(self, secret):
        return not self.server.secret or secret == self.server.secret

    def read_json_or_form(self):
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return self.read_json()
        return self.read_form()

    def read_json(self):
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def read_form(self):
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(length)
        if "multipart/form-data" in content_type:
            env = {"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(length)}
            form = cgi.FieldStorage(fp=io.BytesIO(body), headers=self.headers, environ=env)
            return {key: form.getvalue(key) for key in form.keys()}
        return {k: v[0] if v else "" for k, v in urllib.parse.parse_qs(body.decode("utf-8")).items()}

    def path_only(self):
        return urllib.parse.urlparse(self.path).path

    def query(self):
        return urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query, keep_blank_values=True)

    def json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def html(self, content, status=200):
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"{self.client_address[0]} {fmt % args}", flush=True)


def esc(value):
    return html.escape(str(value or ""), quote=True)


def simple_page(title, heading, message):
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{BASE_CSS}</style></head><body><main><h1>{esc(heading)}</h1><p class="message">{esc(message)}</p></main></body></html>"""


def error_page(title, message):
    return simple_page(title, title, message)


def home_page():
    return simple_page(
        "BarkBridge Relay",
        "BarkBridge Relay",
        "中继服务正在运行。可用路径：/chat?secret=你的密钥 /settings?secret=你的密钥 /control?secret=你的密钥 /poll?secret=你的密钥&waitMs=0",
    )


def control_page(secret):
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BarkBridge Control</title><style>{CONTROL_CSS}</style></head><body><main><header><h1>BarkBridge Control</h1><a href="/chat?secret={esc(secret)}">返回聊天</a></header><section class="grid" id="status"></section><p class="message">这些指令会进入中转队列，由 Mac relay 下一次轮询后执行。</p><form method="post" action="/control"><input type="hidden" name="secret" value="{esc(secret)}"><button name="action" value="pause">暂停 Mac relay</button><button name="action" value="resume">恢复 Mac relay</button><button name="action" value="auto_send_on">开启自动发送</button><button name="action" value="auto_send_off">关闭自动发送</button><button name="action" value="manual_only_on">开启仅手动模式</button><button name="action" value="manual_only_off">关闭仅手动模式</button></form></main><script>const secret={json.dumps(secret)};{CONTROL_JS}</script></body></html>"""


def settings_page(secret):
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,viewport-fit=cover"><title>BarkBridge Settings</title><style>{SETTINGS_CSS}</style></head><body><main><header><h1>BarkBridge 设置</h1><a href="/chat?secret={esc(secret)}">返回聊天</a></header><section><label>置顶联系人</label><textarea id="pinned" placeholder="每行一个联系人"></textarea></section><section><label>隐藏联系人</label><textarea id="hidden" placeholder="每行一个联系人"></textarea></section><button id="save">保存设置</button><p id="status"></p></main><script>const secret={json.dumps(secret)};{SETTINGS_JS}</script></body></html>"""


def reply_page(query):
    token = query.get("token", [""])[0]
    if not token:
        return error_page("没有可用的回复令牌", "这个页面需要从 Bark 通知点击进入。")
    return compose_like_page("BarkBridge Reply", "reply", "", token, query.get("contact", ["WeChat"])[0])


def compose_page(secret, contact):
    return compose_like_page("BarkBridge Compose", "compose", secret, "", contact)


def compose_like_page(title, mode, secret, token, selected):
    options = list(DEFAULT_CONTACTS)
    if selected and selected not in options and not is_hidden_contact(selected):
        options.insert(0, selected)
    contacts = "".join(
        f'<button class="contact {"active" if c == selected else ""}" data-contact="{esc(c)}" type="button"><span>{esc(c)}</span></button>'
        for c in options
    )
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,viewport-fit=cover"><title>{esc(title)}</title><style>{CHAT_CSS}</style></head><body><div class="app" data-mode="{esc(mode)}" data-secret="{esc(secret)}" data-token="{esc(token)}"><header><h1 id="title">{esc(selected)}</h1></header><nav class="contacts" id="contacts">{contacts}</nav><main class="messages" id="messages"></main><form id="form"><textarea id="text" placeholder="输入要发送的内容"></textarea><button class="send" type="submit">发送</button></form></div><script>{COMPOSE_JS}</script></body></html>"""


def chat_page(secret, selected):
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,viewport-fit=cover"><title>BarkBridge Chat</title><style>{CHAT_CSS}</style></head><body><div class="app"><header><div class="topbar"><h1 id="title">BarkBridge Chat</h1><a class="settings" href="/settings?secret={esc(secret)}">设置</a></div><input id="search" class="search" placeholder="搜索联系人"><div class="hint">只显示 BarkBridge 启用后经手的完整消息</div></header><nav class="contacts" id="contacts"></nav><div class="chat-tools"><button id="latestChat" class="ghost primary" type="button">回到最新</button><button id="clearChat" class="ghost" type="button">清空当前联系人记录</button></div><main class="messages" id="messages"></main><form id="form"><textarea id="text" placeholder="输入回复内容"></textarea><button class="send" type="submit">发送</button></form></div><script>const secret={json.dumps(secret)};let selected={json.dumps(selected)};{CHAT_JS}</script></body></html>"""


BASE_CSS = """
body{margin:0;background:#f3f7f6;color:#17201f;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:560px;margin:0 auto;padding:28px 18px}
h1{font-size:24px;margin:0 0 14px}.message{padding:14px;border:1px solid #d5e4e1;background:#fff;border-radius:8px;line-height:1.5}
button{width:100%;height:48px;margin-top:12px;border:0;border-radius:8px;background:#007670;color:#fff;font-family:inherit;font-size:16px;font-weight:600}
"""


CONTROL_CSS = """
body{margin:0;background:#f3f7f6;color:#17201f;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:680px;margin:0 auto;padding:28px 18px}header{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center}h1{font-size:24px;margin:0}a{color:#007670;font-weight:800;text-decoration:none}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:16px 0}.metric{border:1px solid #d5e4e1;background:#fff;border-radius:8px;padding:12px}.metric strong{display:block;font-size:13px;color:#667370;margin-bottom:6px}.metric span{font-size:17px;font-weight:800;overflow-wrap:anywhere}
.message{padding:14px;border:1px solid #d5e4e1;background:#fff;border-radius:8px;line-height:1.5}button{width:100%;height:48px;margin-top:12px;border:0;border-radius:8px;background:#007670;color:#fff;font-family:inherit;font-size:16px;font-weight:600}
@media(max-width:520px){.grid{grid-template-columns:1fr}}
"""


CONTROL_JS = r"""
const statusEl=document.getElementById("status");
function fmt(ts){if(!ts)return "-";const d=new Date(ts);return String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")+" "+String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0")+":"+String(d.getSeconds()).padStart(2,"0")}
function esc(v){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
async function loadStatus(){const r=await fetch("/api/status?secret="+encodeURIComponent(secret),{cache:"no-store"});const s=await r.json();const rows=[["服务时间",fmt(s.time)],["待发送队列",s.queueCount],["Android最后上传",fmt(s.androidLastUploadAt)],["Mac最后轮询",fmt(s.macLastPollAt)],["最近发送入队",fmt(s.outgoingLastQueuedAt)],["联系人数量",s.contactCount],["单联系人保留",s.historyLimitPerContact+" 条"],["总记录上限",s.historyLimitTotal+" 条"]];statusEl.innerHTML=rows.map(([k,v])=>'<div class="metric"><strong>'+esc(k)+'</strong><span>'+esc(v)+'</span></div>').join("")}
loadStatus();setInterval(loadStatus,5000);
"""


CHAT_CSS = """
:root{color-scheme:dark;--bg:#151719;--panel:#202327;--line:#34383d;--text:#f4f5f6;--muted:#a9b0b6;--green:#07c160;--in:#2b2f33;--out:#12b969}
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:var(--bg);color:var(--text);font:17px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-text-size-adjust:100%}
.app{height:100dvh;min-height:100svh;display:grid;grid-template-rows:auto auto auto minmax(0,1fr) auto;overflow:hidden}
header{z-index:2;background:var(--panel);border-bottom:1px solid var(--line);padding:calc(12px + env(safe-area-inset-top)) 14px 12px}
h1{margin:0;font-size:21px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.hint{color:var(--muted);font-size:13px;margin-top:4px}
.topbar{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center}.settings{color:var(--green);font-size:15px;font-weight:800;text-decoration:none}.ghost{height:38px;border:1px solid #46505a;border-radius:8px;background:#2a2d31;color:var(--text);font:15px inherit;font-weight:800;padding:0 12px}.search{width:100%;height:42px;margin-top:10px;border:1px solid var(--line);border-radius:8px;background:#2a2d31;color:var(--text);font:17px inherit;padding:0 12px}
.contacts{display:flex;gap:8px;overflow:auto;padding:10px 12px;background:var(--panel);border-bottom:1px solid var(--line)}
.chat-tools{display:grid;grid-template-columns:112px 1fr;gap:8px;background:var(--panel);border-bottom:1px solid var(--line);padding:8px 12px}.chat-tools .ghost{width:100%}.ghost.primary{background:var(--green);border-color:var(--green);color:#03150a}
.contact{white-space:nowrap;border:1px solid var(--line);border-radius:999px;background:#2a2d31;color:var(--text);padding:8px 12px;font:15px inherit}.contact.active{background:var(--green);color:#03150a;border-color:var(--green);font-weight:800}
.messages{min-height:0;overflow:auto;-webkit-overflow-scrolling:touch;padding:14px 12px 14px;display:flex;flex-direction:column;gap:10px}.msg{max-width:88%;display:grid;gap:4px}.msg.in{align-self:flex-start}.msg.out{align-self:flex-end}.bottom-anchor{height:1px;min-height:1px}
.bubble{border-radius:8px;padding:10px 12px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:18px}.in .bubble{background:var(--in)}.out .bubble{background:var(--out);color:#03150a}.meta{color:var(--muted);font-size:12px}.out .meta{text-align:right}
form{display:grid;grid-template-columns:1fr 76px;gap:8px;background:var(--panel);border-top:1px solid var(--line);padding:10px 12px calc(10px + env(safe-area-inset-bottom))}
textarea{height:72px;resize:none;border:1px solid var(--line);border-radius:8px;background:#2a2d31;color:var(--text);font-family:inherit;font-size:21px;line-height:1.4;padding:10px 12px}button.send{height:72px;border:0;border-radius:8px;background:var(--green);color:#03150a;font-weight:800;font-size:17px}
@media(min-width:900px){body{display:grid;place-items:center}.app{width:min(940px,calc(100vw - 32px));height:min(780px,calc(100vh - 32px));min-height:0;border:1px solid var(--line);border-radius:8px;overflow:hidden}.messages{padding-bottom:14px}}
"""


CHAT_JS = r"""
let history=[],contacts=[],initialLoad=true;const contactsEl=document.getElementById("contacts"),messagesEl=document.getElementById("messages"),titleEl=document.getElementById("title"),textEl=document.getElementById("text"),searchEl=document.getElementById("search"),clearChatEl=document.getElementById("clearChat"),latestChatEl=document.getElementById("latestChat");
function esc(v){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}function fmt(t){const d=new Date(t||Date.now());return String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")+" "+String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0")}
function nearBottom(){return messagesEl.scrollHeight-messagesEl.scrollTop-messagesEl.clientHeight<120}
function scrollToBottom(force=false){if(!force&&!nearBottom())return;const run=()=>{const last=messagesEl.querySelector("[data-last='1']");if(last)last.scrollIntoView({block:"end",inline:"nearest"});messagesEl.scrollTop=messagesEl.scrollHeight};requestAnimationFrame(()=>{run();[50,120,250,500,900,1400].forEach(ms=>setTimeout(run,ms))})}
async function load(options={}){const shouldStick=initialLoad||options.forceScroll||nearBottom();const [chatRes,contactRes]=await Promise.all([fetch("/api/chat?secret="+encodeURIComponent(secret),{cache:"no-store"}),fetch("/api/contacts?secret="+encodeURIComponent(secret),{cache:"no-store"})]);const data=await chatRes.json();const contactData=await contactRes.json();history=data.history||[];contacts=[...new Set([selected,...(contactData.contacts||[]),...history.map(i=>i.contact)].filter(Boolean))];if(!selected&&contacts.length)selected=contacts[0];renderContacts();render(shouldStick);initialLoad=false}
function renderContacts(){const q=(searchEl.value||"").trim().toLowerCase();const visible=contacts.filter(c=>!q||c.toLowerCase().includes(q));contactsEl.innerHTML=visible.map(c=>'<button type="button" class="contact '+(c===selected?'active':'')+'" data-contact="'+esc(c)+'">'+esc(c)+'</button>').join("");contactsEl.querySelectorAll(".contact").forEach(b=>b.onclick=()=>{selected=b.dataset.contact;renderContacts();render(true)})}
function render(stick=false){titleEl.textContent=selected||"BarkBridge Chat";contactsEl.querySelectorAll(".contact").forEach(b=>b.classList.toggle("active",b.dataset.contact===selected));clearChatEl.disabled=!selected;const items=history.filter(i=>!selected||i.contact===selected).reverse();messagesEl.innerHTML=(items.map((i,idx)=>'<article class="msg '+(i.direction==="incoming"?'in':'out')+'" '+(idx===items.length-1?'data-last="1"':'')+'><div class="bubble">'+esc(i.text||"")+'</div><div class="meta">'+esc(i.contact||"")+' · '+esc(i.status||"")+' · '+fmt(i.createdAt)+'</div></article>').join("")||'<div class="hint" data-last="1">暂无消息</div>')+'<div class="bottom-anchor"></div>';scrollToBottom(stick)}
async function clearCurrentChat(){if(!selected)return;if(!confirm("只清除「"+selected+"」的聊天记录？"))return;clearChatEl.disabled=true;const r=await fetch("/api/chat/clear",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({secret,contact:selected})});if(!r.ok)alert("清除失败");await load({forceScroll:true});clearChatEl.disabled=false}
searchEl.oninput=renderContacts;clearChatEl.onclick=clearCurrentChat;latestChatEl.onclick=()=>scrollToBottom(true);if(window.visualViewport)visualViewport.addEventListener("resize",()=>scrollToBottom(true));window.addEventListener("orientationchange",()=>setTimeout(()=>scrollToBottom(true),300));window.addEventListener("pageshow",()=>scrollToBottom(true));document.getElementById("form").onsubmit=async e=>{e.preventDefault();const text=textEl.value.trim();if(!selected||!text)return;const form=new FormData();form.set("secret",secret);form.set("contact",selected);form.set("text",text);const r=await fetch("/send",{method:"POST",body:form});if(!r.ok)alert("提交失败");else{textEl.value="";await load({forceScroll:true})}};load({forceScroll:true});setInterval(()=>load(),5000);
"""


SETTINGS_CSS = """
:root{color-scheme:dark;--bg:#151719;--panel:#202327;--line:#34383d;--text:#f4f5f6;--muted:#a9b0b6;--green:#07c160}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:18px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-text-size-adjust:100%}
main{max-width:680px;margin:0 auto;padding:calc(16px + env(safe-area-inset-top)) 14px calc(18px + env(safe-area-inset-bottom))}
header{display:grid;grid-template-columns:1fr auto;align-items:center;gap:12px;margin-bottom:14px}h1{margin:0;font-size:24px}a{color:var(--green);font-weight:800;text-decoration:none}
section{margin-top:14px}label{display:block;margin-bottom:8px;color:var(--muted);font-size:14px}textarea{width:100%;min-height:180px;resize:vertical;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--text);font:18px/1.5 inherit;padding:12px}
button{width:100%;height:52px;margin-top:16px;border:0;border-radius:8px;background:var(--green);color:#03150a;font-size:18px;font-weight:900}#status{min-height:24px;color:var(--muted)}
"""


SETTINGS_JS = r"""
const pinned=document.getElementById("pinned"),hidden=document.getElementById("hidden"),statusEl=document.getElementById("status");
function lines(value){return String(value||"").split(/\n/).map(v=>v.trim()).filter(Boolean)}
async function load(){const r=await fetch("/api/config?secret="+encodeURIComponent(secret),{cache:"no-store"});const data=await r.json();const c=data.config||{};pinned.value=(c.pinnedContacts||[]).join("\n");hidden.value=(c.hiddenContacts||[]).join("\n")}
document.getElementById("save").onclick=async()=>{statusEl.textContent="正在保存";const r=await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({secret,pinnedContacts:lines(pinned.value),hiddenContacts:lines(hidden.value)})});statusEl.textContent=r.ok?"已保存":"保存失败"};
load();
"""


COMPOSE_JS = r"""
const app=document.querySelector(".app"),mode=app.dataset.mode,secret=app.dataset.secret,token=app.dataset.token,textEl=document.getElementById("text"),titleEl=document.getElementById("title");let selected=titleEl.textContent;
document.querySelectorAll(".contact").forEach(b=>b.onclick=()=>{selected=b.dataset.contact;titleEl.textContent=selected;document.querySelectorAll(".contact").forEach(x=>x.classList.toggle("active",x===b))});
document.getElementById("form").onsubmit=async e=>{e.preventDefault();const text=textEl.value.trim();if(!selected||!text)return;const form=new FormData();form.set("contact",selected);form.set("text",text);if(mode==="reply")form.set("token",token);else form.set("secret",secret);const r=await fetch(mode==="reply"?"/reply":"/send",{method:"POST",body:form});if(!r.ok)alert("提交失败");else{textEl.value="";alert("已提交，等待 Mac 微信执行")}};
"""


class RelayServer(ThreadingHTTPServer):
    def __init__(self, address, handler, store, secret):
        super().__init__(address, handler)
        self.store = store
        self.secret = secret


def main():
    parser = argparse.ArgumentParser(description="Self-hosted BarkBridge relay server.")
    parser.add_argument("--host", default=os.environ.get("BARKBRIDGE_RELAY_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("BARKBRIDGE_RELAY_PORT", "8787")))
    parser.add_argument("--db", default=os.environ.get("BARKBRIDGE_RELAY_DB", "/opt/barkbridge-relay/relay.sqlite3"))
    parser.add_argument("--secret", default=os.environ.get("BARKBRIDGE_RELAY_SECRET", ""))
    args = parser.parse_args()
    store = RelayStore(args.db)
    server = RelayServer((args.host, args.port), RelayHandler, store, args.secret)
    print(f"BarkBridge relay listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
