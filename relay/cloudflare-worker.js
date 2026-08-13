export class RelayRoom {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.queue = [];
    this.waiters = [];
  }

  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/enqueue" && request.method === "POST") {
      const reply = await request.json();
      await this.enqueue(reply);
      return Response.json({ ok: true });
    }
    if (url.pathname === "/record" && request.method === "POST") {
      const message = await request.json();
      await this.addHistory(message);
      return Response.json({ ok: true });
    }
    if (url.pathname === "/history" && request.method === "GET") {
      return Response.json({ history: await this.history() });
    }
    if (url.pathname === "/chat-history" && request.method === "GET") {
      return Response.json({ history: await this.history() });
    }
    if (url.pathname === "/contacts" && request.method === "GET") {
      return Response.json({ contacts: this.contacts() });
    }
    if (url.pathname === "/dequeue" && request.method === "GET") {
      if (this.queue.length > 0) {
        return Response.json({ replies: this.queue.splice(0, this.queue.length) });
      }
      const waitMs = Math.max(0, Math.min(25000, Number(url.searchParams.get("waitMs") || 25000)));
      return this.waitForReply(waitMs);
    }
    return new Response("Not found", { status: 404 });
  }

  async enqueue(reply) {
    this.pruneWaiters();
    await this.addHistory(reply);
    const waiter = this.waiters.shift();
    if (waiter) {
      clearTimeout(waiter.timer);
      waiter.resolve(Response.json({ replies: [reply] }));
      return;
    }
    this.queue.push(reply);
    while (this.queue.length > 200) this.queue.shift();
  }

  async addHistory(reply) {
    const history = await this.state.storage.get("history") || [];
    history.push({
      id: String(reply.id || crypto.randomUUID()),
      contact: String(reply.contact || "").trim(),
      text: String(reply.text || "").trim(),
      source: String(reply.source || "reply"),
      direction: String(reply.direction || directionFromSource(reply.source)).trim(),
      status: String(reply.status || statusFromSource(reply.source)).trim(),
      createdAt: Number(reply.createdAt || Date.now()),
    });
    while (history.length > 300) history.shift();
    await this.state.storage.put("history", history);
  }

  async history() {
    const history = await this.state.storage.get("history") || [];
    return history.slice(-120).reverse();
  }

  contacts() {
    const contacts = [];
    for (const reply of this.queue) {
      const contact = String(reply.contact || "").trim();
      if (contact && !contacts.includes(contact)) contacts.push(contact);
    }
    return contacts;
  }

  waitForReply(waitMs = 25000) {
    if (waitMs <= 0) return Response.json({ replies: [] });
    return new Promise((resolve) => {
      const waiter = {
        resolve,
        expiresAt: Date.now() + waitMs,
      };
      waiter.timer = setTimeout(() => {
        const index = this.waiters.indexOf(waiter);
        if (index >= 0) this.waiters.splice(index, 1);
        resolve(Response.json({ replies: [] }));
      }, waitMs);
      this.waiters.push(waiter);
    });
  }

  pruneWaiters() {
    const now = Date.now();
    for (let i = this.waiters.length - 1; i >= 0; i--) {
      if (this.waiters[i].expiresAt <= now) {
        clearTimeout(this.waiters[i].timer);
        this.waiters[i].resolve(Response.json({ replies: [] }));
        this.waiters.splice(i, 1);
      }
    }
  }
}

function directionFromSource(source) {
  if (source === "android") return "incoming";
  if (source === "reply" || source === "compose") return "outgoing";
  return "system";
}

function statusFromSource(source) {
  if (source === "android") return "received";
  if (source === "reply" || source === "compose") return "queued";
  return "event";
}

const DEFAULT_CONTACTS = [
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
];

const HIDDEN_CONTACTS = new Set([
  "BarkBridge配置测试",
  "BarkBridge手机自测",
  "阿里云部署测试",
  "Codex上传复测",
  "本地测试",
]);
const HIDDEN_CONTACT_PREFIXES = ["BarkBridge", "Codex", "阿里云部署测试", "本地测试"];

function isHiddenContact(contact) {
  const name = String(contact || "").trim();
  return Boolean(name && (HIDDEN_CONTACTS.has(name) || HIDDEN_CONTACT_PREFIXES.some(prefix => name.startsWith(prefix))));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "HEAD" && ["/", "/reply", "/compose", "/control", "/chat"].includes(url.pathname)) {
      return new Response(null, { status: 200, headers: { "content-type": "text/html; charset=utf-8" } });
    }
    if (url.pathname === "/" && request.method === "GET") {
      return homePage();
    }
    if (url.pathname === "/reply" && request.method === "GET") {
      return replyPage(url);
    }
    if (url.pathname === "/reply" && request.method === "POST") {
      return saveReply(request, env);
    }
    if (url.pathname === "/ingest" && request.method === "POST") {
      return saveIncomingMessage(request, env);
    }
    if (url.pathname === "/chat" && request.method === "GET") {
      return chatPage(url, env);
    }
    if (url.pathname === "/api/chat" && request.method === "GET") {
      return chatJson(url, env);
    }
    if (url.pathname === "/compose" && request.method === "GET") {
      return composePage(url, env);
    }
    if (url.pathname === "/control" && request.method === "GET") {
      return controlPage(url, env);
    }
    if (url.pathname === "/control" && request.method === "POST") {
      return saveControlCommand(request, env);
    }
    if (url.pathname === "/send" && request.method === "POST") {
      return saveManualMessage(request, env);
    }
    if (url.pathname === "/api/contacts" && request.method === "GET") {
      return contactsJson(url, env);
    }
    if (url.pathname === "/api/history" && request.method === "GET") {
      return historyJson(url, env);
    }
    if (url.pathname === "/poll" && request.method === "GET") {
      return pollReplies(url, env);
    }
    return new Response("Not found", { status: 404 });
  },
};

function relayStub(env) {
  const id = env.RELAY.idFromName("barkbridge-main");
  return env.RELAY.get(id);
}

async function saveReply(request, env) {
  try {
    const form = await request.formData();
    const token = String(form.get("token") || "").trim();
    const contact = String(form.get("contact") || "").trim();
    const text = String(form.get("text") || "").trim();
    if (!token) return errorPage("缺少回复令牌", "请从 BarkBridge 推送通知里的回复链接打开，不要直接打开回复页面。");
    if (!text) return errorPage("缺少回复内容", "请输入要发送给微信联系人的回复内容。");

    const id = `${Date.now()}-${crypto.randomUUID()}`;
    await relayStub(env).fetch("https://relay.local/enqueue", {
      method: "POST",
      body: JSON.stringify({ id, token, contact, text, direction: "outgoing", status: "queued", createdAt: Date.now() }),
      headers: { "content-type": "application/json" },
    });
    return html("Reply saved", "<main><h1>Reply saved</h1><p>You can close this page.</p></main>");
  } catch (error) {
    return workerError(error);
  }
}


async function saveIncomingMessage(request, env) {
  try {
    const data = await request.json();
    const secret = String(data.secret || "").trim();
    const contact = String(data.contact || "").trim();
    const text = String(data.text || "").trim();
    if (env.REPLY_SECRET && secret !== env.REPLY_SECRET) {
      return Response.json({ ok: false, error: "密钥不正确" }, { status: 403 });
    }
    if (!contact || !text) {
      return Response.json({ ok: false, error: "联系人和内容不能为空" }, { status: 400 });
    }
    const id = `${Date.now()}-${crypto.randomUUID()}`;
    await relayStub(env).fetch("https://relay.local/record", {
      method: "POST",
      body: JSON.stringify({ id, token: "mirror", contact, text, direction: "incoming", status: "received", source: "android", createdAt: Number(data.createdAt || Date.now()) }),
      headers: { "content-type": "application/json" },
    });
    return Response.json({ ok: true });
  } catch (error) {
    return workerError(error);
  }
}


async function saveManualMessage(request, env) {
  try {
    const contentType = request.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
      ? await request.json()
      : Object.fromEntries(await request.formData());
    const secret = String(data.secret || "").trim();
    const contact = String(data.contact || "").trim();
    const text = String(data.text || "").trim();
    if (env.REPLY_SECRET && secret !== env.REPLY_SECRET) {
      return Response.json({ ok: false, error: "密钥不正确" }, { status: 403 });
    }
    if (!contact || !text) {
      return Response.json({ ok: false, error: "联系人和内容不能为空" }, { status: 400 });
    }
    const id = `${Date.now()}-${crypto.randomUUID()}`;
    await relayStub(env).fetch("https://relay.local/enqueue", {
      method: "POST",
      body: JSON.stringify({ id, token: "manual", contact, text, direction: "outgoing", status: "queued", createdAt: Date.now(), source: "compose" }),
      headers: { "content-type": "application/json" },
    });
    return Response.json({ ok: true });
  } catch (error) {
    return workerError(error);
  }
}


async function saveControlCommand(request, env) {
  try {
    const contentType = request.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
      ? await request.json()
      : Object.fromEntries(await request.formData());
    const secret = String(data.secret || "").trim();
    const action = String(data.action || "").trim();
    const rawValue = String(data.value || "").trim();
    if (env.REPLY_SECRET && secret !== env.REPLY_SECRET) {
      return Response.json({ ok: false, error: "密钥不正确" }, { status: 403 });
    }
    if (!["pause", "resume", "auto_send_on", "auto_send_off", "manual_only_on", "manual_only_off"].includes(action)) {
      return Response.json({ ok: false, error: "未知控制指令" }, { status: 400 });
    }
    const value = rawValue === "true" || rawValue === "1" || rawValue === "on" || action.endsWith("_on") || action === "pause";
    const id = `${Date.now()}-${crypto.randomUUID()}`;
    await relayStub(env).fetch("https://relay.local/enqueue", {
      method: "POST",
      body: JSON.stringify({ id, token: "control", source: "control", action, value, text: `${action}=${value}`, createdAt: Date.now() }),
      headers: { "content-type": "application/json" },
    });
    return Response.json({ ok: true });
  } catch (error) {
    return workerError(error);
  }
}


async function contactsJson(url, env) {
  if (env.REPLY_SECRET && url.searchParams.get("secret") !== env.REPLY_SECRET) {
    return Response.json({ contacts: [] }, { status: 403 });
  }
  const response = await relayStub(env).fetch("https://relay.local/contacts");
  return response;
}

async function historyJson(url, env) {
  if (env.REPLY_SECRET && url.searchParams.get("secret") !== env.REPLY_SECRET) {
    return Response.json({ history: [] }, { status: 403 });
  }
  return relayStub(env).fetch("https://relay.local/history");
}

async function chatJson(url, env) {
  if (env.REPLY_SECRET && url.searchParams.get("secret") !== env.REPLY_SECRET) {
    return Response.json({ history: [] }, { status: 403 });
  }
  const response = await relayStub(env).fetch("https://relay.local/chat-history");
  const data = await response.json();
  const contact = String(url.searchParams.get("contact") || "").trim();
  const history = Array.isArray(data.history) ? data.history : [];
  return Response.json({
    history: contact
      ? history.filter(item => String(item.contact || "") === contact)
      : history.filter(item => !isHiddenContact(item.contact)),
  });
}

async function pollReplies(url, env) {
  if (env.REPLY_SECRET && url.searchParams.get("secret") !== env.REPLY_SECRET) {
    return Response.json({ replies: [] }, { status: 403 });
  }

  try {
    const waitMs = url.searchParams.get("waitMs");
    const target = waitMs === null
      ? "https://relay.local/dequeue"
      : `https://relay.local/dequeue?waitMs=${encodeURIComponent(waitMs)}`;
    return await relayStub(env).fetch(target);
  } catch (error) {
    return workerError(error);
  }
}

function replyPage(url) {
  const rawToken = url.searchParams.get("token") || "";
  if (!rawToken) {
    return errorPage("没有可用的回复令牌", "这个页面需要从 Bark 通知点击进入。正常链接会带有 token、contact 和 message 参数。");
  }
  const token = escapeHtml(rawToken);
  const contact = escapeHtml(url.searchParams.get("contact") || "WeChat");
  const message = escapeHtml(url.searchParams.get("message") || "");
  return wechatPage({
    title: "BarkBridge Reply",
    mode: "reply",
    secret: "",
    token,
    selectedContact: contact,
    message,
  });
}

function composePage(url, env) {
  const secret = url.searchParams.get("secret") || "";
  if (env.REPLY_SECRET && secret !== env.REPLY_SECRET) {
    return errorPage("密钥不正确", "请使用带 secret 参数的 BarkBridge 主动发送页面。");
  }
  return wechatPage({
    title: "BarkBridge Compose",
    mode: "compose",
    secret: escapeHtml(secret),
    token: "",
    selectedContact: escapeHtml(url.searchParams.get("contact") || "文件传输助手"),
    message: "",
  });
}


function chatPage(url, env) {
  const secret = url.searchParams.get("secret") || "";
  if (env.REPLY_SECRET && secret !== env.REPLY_SECRET) {
    return errorPage("密钥不正确", "请使用带 secret 参数的 BarkBridge 聊天面板。");
  }
  const selectedContact = url.searchParams.get("contact") || "";
  const selectedJson = JSON.stringify(selectedContact);
  return new Response(`<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover">
  <title>BarkBridge Chat</title>
  <style>
    :root{color-scheme:dark;--bg:#151719;--panel:#202327;--line:#34383d;--text:#f4f5f6;--muted:#a9b0b6;--green:#07c160;--in:#2b2f33;--out:#12b969}
    *{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;background:var(--bg);color:var(--text);font:17px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-text-size-adjust:100%}
    .app{min-height:100svh;display:grid;grid-template-rows:auto auto minmax(0,1fr) auto}
    header{position:sticky;top:0;z-index:2;background:var(--panel);border-bottom:1px solid var(--line);padding:calc(12px + env(safe-area-inset-top)) 14px 12px}
    h1{margin:0;font-size:21px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.hint{color:var(--muted);font-size:13px;margin-top:4px}
    .contacts{display:flex;gap:8px;overflow:auto;padding:10px 12px;background:var(--panel);border-bottom:1px solid var(--line)}
    .contact{white-space:nowrap;border:1px solid var(--line);border-radius:999px;background:#2a2d31;color:var(--text);padding:8px 12px;font:15px inherit}.contact.active{background:var(--green);color:#03150a;border-color:var(--green);font-weight:800}
    .messages{overflow:auto;padding:14px 12px 118px;display:flex;flex-direction:column;gap:10px}.msg{max-width:88%;display:grid;gap:4px}.msg.in{align-self:flex-start}.msg.out{align-self:flex-end}
    .bubble{border-radius:8px;padding:10px 12px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:18px}.in .bubble{background:var(--in)}.out .bubble{background:var(--out);color:#03150a}.meta{color:var(--muted);font-size:12px}.out .meta{text-align:right}
    form{position:fixed;left:0;right:0;bottom:0;display:grid;grid-template-columns:1fr 76px;gap:8px;background:var(--panel);border-top:1px solid var(--line);padding:10px 12px calc(10px + env(safe-area-inset-bottom))}
    textarea{height:72px;resize:none;border:1px solid var(--line);border-radius:8px;background:#2a2d31;color:var(--text);font-family:inherit;font-size:21px;line-height:1.4;padding:10px 12px}button.send{height:72px;border:0;border-radius:8px;background:var(--green);color:#03150a;font-weight:800;font-size:17px}
    @media(min-width:900px){body{display:grid;place-items:center}.app{width:min(940px,calc(100vw - 32px));height:min(780px,calc(100vh - 32px));min-height:0;border:1px solid var(--line);border-radius:8px;overflow:hidden}form{position:static}.messages{padding-bottom:14px}}
  </style>
</head>
<body><div class="app"><header><h1 id="title">BarkBridge Chat</h1><div class="hint">只显示 BarkBridge 启用后经手的完整消息</div></header><nav class="contacts" id="contacts"></nav><main class="messages" id="messages"></main><form id="form"><textarea id="text" placeholder="输入回复内容"></textarea><button class="send" type="submit">发送</button></form></div>
<script>
const secret=${JSON.stringify(secret)};let selected=${selectedJson};const defaultContacts=${JSON.stringify(DEFAULT_CONTACTS)};let history=[];const contactsEl=document.getElementById("contacts"),messagesEl=document.getElementById("messages"),titleEl=document.getElementById("title"),textEl=document.getElementById("text");
function esc(v){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}function fmt(t){const d=new Date(t||Date.now());return String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")+" "+String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0")}
async function load(){const r=await fetch("/api/chat?secret="+encodeURIComponent(secret),{cache:"no-store"});const data=await r.json();history=data.history||[];const contacts=[...new Set([selected,...defaultContacts,...history.map(i=>i.contact)].filter(Boolean))];if(!selected&&contacts.length)selected=contacts[0];contactsEl.innerHTML=contacts.map(c=>'<button type="button" class="contact '+(c===selected?'active':'')+'" data-contact="'+esc(c)+'">'+esc(c)+'</button>').join("");contactsEl.querySelectorAll(".contact").forEach(b=>b.onclick=()=>{selected=b.dataset.contact;render()});render()}
function render(){titleEl.textContent=selected||"BarkBridge Chat";contactsEl.querySelectorAll(".contact").forEach(b=>b.classList.toggle("active",b.dataset.contact===selected));const items=history.filter(i=>!selected||i.contact===selected).reverse();messagesEl.innerHTML=items.map(i=>'<article class="msg '+(i.direction==="incoming"?'in':'out')+'"><div class="bubble">'+esc(i.text||"")+'</div><div class="meta">'+esc(i.contact||"")+' · '+esc(i.status||"")+' · '+fmt(i.createdAt)+'</div></article>').join("")||'<div class="hint">暂无消息</div>';messagesEl.scrollTop=messagesEl.scrollHeight}
document.getElementById("form").onsubmit=async e=>{e.preventDefault();const text=textEl.value.trim();if(!selected||!text)return;const form=new FormData();form.set("secret",secret);form.set("contact",selected);form.set("text",text);const r=await fetch("/send",{method:"POST",body:form});if(!r.ok)alert("提交失败");else{textEl.value="";await load()}};load();setInterval(load,5000);
</script></body></html>`, { headers: { "content-type": "text/html; charset=utf-8" } });
}


function controlPage(url, env) {
  const secret = url.searchParams.get("secret") || "";
  if (env.REPLY_SECRET && secret !== env.REPLY_SECRET) {
    return errorPage("密钥不正确", "请使用带 secret 参数的 BarkBridge 控制页面。");
  }
  const safeSecret = escapeHtml(secret);
  return html(
    "BarkBridge Control",
    `<main>
      <h1>BarkBridge Control</h1>
      <p class="message">这些指令会进入中转队列，由 Mac relay 下一次轮询后执行。</p>
      <form class="control" method="post" action="/control">
        <input type="hidden" name="secret" value="${safeSecret}">
        <button name="action" value="pause">暂停 Mac relay</button>
        <button name="action" value="resume">恢复 Mac relay</button>
        <button name="action" value="auto_send_on">开启自动发送</button>
        <button name="action" value="auto_send_off">关闭自动发送</button>
        <button name="action" value="manual_only_on">开启仅手动模式</button>
        <button name="action" value="manual_only_off">关闭仅手动模式</button>
      </form>
      <p class="hint">指令执行后，Mac 会通过 Bark 回执通知你。</p>
    </main>`
  );
}


function wechatPage({ title, mode, secret, token, selectedContact, message }) {
  const contacts = [...DEFAULT_CONTACTS];
  if (selectedContact && !contacts.includes(selectedContact) && !isHiddenContact(selectedContact)) contacts.unshift(selectedContact);
  const selectedJson = JSON.stringify(selectedContact || "文件传输助手");
  const contactsHtml = contacts.map((contact, index) => `
    <button class="contact ${contact === selectedContact ? "active" : ""}" data-contact="${escapeHtml(contact)}" type="button">
      <span class="avatar">${escapeHtml(contact.slice(0, 1))}</span>
      <span class="contactText">
        <strong>${escapeHtml(contact)}</strong>
        <small>${index === 0 && message ? escapeHtml(message) : "点击选择联系人"}</small>
      </span>
    </button>`).join("");

  return new Response(`<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover">
  <title>${escapeHtml(title)}</title>
  <style>
    :root{color-scheme:dark;--bg:#101214;--side:#202327;--main:#1b1d20;--line:#33383d;--text:#f4f5f6;--muted:#a9b0b6;--green:#07c160;--bubble:#12b969}
    *{box-sizing:border-box}
    html,body{width:100%;max-width:100%;overflow-x:hidden;-webkit-text-size-adjust:100%;text-size-adjust:100%}
    body{margin:0;min-height:100vh;background:var(--main);color:var(--text);font:18px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    .app{width:100%;max-width:100%;min-height:100svh;display:grid;grid-template-rows:auto minmax(0,1fr) auto;background:var(--main);overflow-x:hidden}
    .top{position:sticky;top:0;z-index:3;background:#202327;border-bottom:1px solid var(--line);padding:calc(12px + env(safe-area-inset-top)) 14px 12px}
    .title{display:grid;grid-template-columns:1fr auto;align-items:center;gap:10px;margin-bottom:10px}
    .title strong{font-size:21px;line-height:1.25;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.title span{color:var(--muted);font-size:14px}
    .search input{width:100%;height:48px;border:0;border-radius:8px;background:#2d3035;color:var(--text);outline:none;padding:0 14px;font-family:inherit;font-size:20px;line-height:1.35}
    .content{min-height:0;overflow:auto;padding-bottom:146px}
    .contacts{display:grid;grid-template-columns:1fr;gap:8px;max-height:36svh;overflow:auto;padding:12px 14px;background:#202327;border-bottom:1px solid var(--line)}
    .contact{width:100%;min-width:0;border:1px solid #3a4046;background:#2a2d31;color:var(--text);display:grid;grid-template-columns:42px minmax(0,1fr);gap:10px;align-items:center;text-align:left;padding:10px 12px;border-radius:8px;cursor:pointer}
    .contact.active{background:#13a765;border-color:#13a765;color:#03150a}.contact:hover{background:#333940}
    .avatar{width:42px;height:42px;border-radius:8px;background:linear-gradient(135deg,#536dfe,#10c77a);display:grid;place-items:center;font-size:17px;font-weight:800;flex:0 0 auto;color:#fff}
    .contactText{min-width:0}.contactText strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:18px;line-height:1.25}.contactText small{display:block;margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px;color:inherit;opacity:.68}
    .log{padding:14px;display:flex;flex-direction:column;gap:10px}
    .entry{border:1px solid var(--line);background:#24272b;border-radius:8px;padding:12px}
    .entryTop{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px}
    .entryTop strong{font-size:16px;color:#eaf7f0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.entryTop time{color:var(--muted);font-size:13px;white-space:nowrap}
    .entryText{white-space:pre-wrap;overflow-wrap:anywhere;color:#f5f6f7;line-height:1.55;font-size:17px}
    .empty{margin:auto;color:var(--muted);text-align:center;padding:34px 0;font-size:17px}
    .composer{position:fixed;left:0;right:0;bottom:0;z-index:4;border-top:1px solid var(--line);background:#202327;padding:12px 14px calc(12px + env(safe-area-inset-bottom));display:grid;grid-template-columns:1fr 78px;gap:10px}
    textarea{width:100%;height:76px;resize:none;border:1px solid var(--line);border-radius:8px;outline:none;background:#2a2d31;color:var(--text);font-family:inherit;font-size:22px;line-height:1.4;padding:11px 12px}
    textarea::placeholder,.search input::placeholder{color:#c2c8cd;font-size:20px;opacity:.82}
    button.send{height:76px;border:0;border-radius:8px;background:var(--green);color:#03150a;font-weight:800;font-size:18px}
    button.send:disabled{opacity:.55}
    .status{position:fixed;left:50%;bottom:calc(96px + env(safe-area-inset-bottom));transform:translateX(-50%);background:#000d;color:#fff;padding:10px 14px;border-radius:999px;font-size:15px;display:none;max-width:calc(100vw - 28px);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    @media(min-width:900px){
      body{display:grid;place-items:center;background:#0d0f11;font-size:16px}
      .app{width:min(920px,calc(100vw - 32px));height:min(780px,calc(100vh - 32px));min-height:0;border:1px solid var(--line);border-radius:8px;overflow:hidden;box-shadow:0 24px 70px #0008;grid-template-rows:auto minmax(0,1fr) auto}
      .top{padding:12px 14px}.title strong{font-size:18px}.title span{font-size:12px}.search input{height:40px;font-size:16px}
      .content{display:grid;grid-template-columns:300px minmax(0,1fr);min-height:0;overflow:hidden;padding-bottom:0}
      .contacts{max-height:none;overflow:auto;border-bottom:0;border-right:1px solid var(--line)}
      .contact{grid-template-columns:38px minmax(0,1fr);padding:10px}.avatar{width:38px;height:38px;font-size:15px}.contactText strong{font-size:15px}.contactText small{font-size:12px}
      .log{overflow:auto;padding-bottom:12px}.entryText{font-size:15px}.empty{font-size:15px}
      .composer{position:static;grid-template-columns:1fr 86px;padding:12px 14px}.composer textarea{height:58px;font-size:16px}.composer textarea::placeholder,.search input::placeholder{font-size:16px}button.send{height:58px;font-size:16px}
      .status{bottom:28px;font-size:13px}
    }
  </style>
</head>
<body>
  <div class="app" data-mode="${escapeHtml(mode)}" data-secret="${secret}" data-token="${token}">
    <header class="top">
      <div class="title"><strong id="title">${selectedContact || "选择联系人"}</strong><span>发送日志</span></div>
      <div class="search"><input id="addContact" placeholder="输入联系人后回车"></div>
    </header>
    <section class="content">
      <nav class="contacts" id="contacts">${contactsHtml}</nav>
      <main class="log" id="log"><div class="empty">正在读取发送日志</div></main>
    </section>
    <form class="composer" id="form">
      <textarea id="text" name="text" placeholder="${mode === "reply" ? "输入回复内容" : "输入要发送的内容"}" required></textarea>
      <button class="send" id="send" type="submit">发送</button>
    </form>
  </div>
  <div class="status" id="status"></div>
  <script>
    const app = document.querySelector(".app");
    const mode = app.dataset.mode;
    const secret = app.dataset.secret;
    const token = app.dataset.token;
    const contactsEl = document.getElementById("contacts");
    const titleEl = document.getElementById("title");
    const textEl = document.getElementById("text");
    const sendEl = document.getElementById("send");
    const statusEl = document.getElementById("status");
    const addContactEl = document.getElementById("addContact");
    const logEl = document.getElementById("log");
    let selected = ${selectedJson};
    let historyItems = [];

    function showStatus(text){statusEl.textContent=text;statusEl.style.display="block";setTimeout(()=>statusEl.style.display="none",2400)}
    function escapeText(value){
      return String(value).replace(/[&<>"']/g, c => {
        if(c==="&") return "&amp;";
        if(c==="<") return "&lt;";
        if(c===">") return "&gt;";
        if(c==='"') return "&quot;";
        return "&#39;";
      });
    }
    function formatTime(value){
      const date = new Date(value || Date.now());
      const pad = n => String(n).padStart(2, "0");
      return pad(date.getMonth()+1) + "-" + pad(date.getDate()) + " " + pad(date.getHours()) + ":" + pad(date.getMinutes());
    }
    function renderHistory(){
      const filtered = historyItems.filter(item => !selected || item.contact === selected);
      const items = filtered.length ? filtered : historyItems;
      if(!items.length){
        logEl.innerHTML = '<div class="empty">暂无发送记录</div>';
        return;
      }
      logEl.innerHTML = items.map(item =>
        '<article class="entry">' +
          '<div class="entryTop">' +
            '<strong>' + escapeText(item.contact || "未知联系人") + '</strong>' +
            '<time>' + escapeText(formatTime(item.createdAt)) + '</time>' +
          '</div>' +
          '<div class="entryText">' + escapeText(item.text || "") + '</div>' +
        '</article>'
      ).join("");
    }
    async function refreshHistory(){
      try{
        const response = await fetch("/api/history?secret=" + encodeURIComponent(secret), {cache:"no-store"});
        if(!response.ok) return;
        const data = await response.json();
        historyItems = data.history || [];
        renderHistory();
      }catch(_error){}
    }
    function select(contact){
      selected=contact;
      app.dataset.selectedContact=contact;
      titleEl.textContent=contact;
      document.querySelectorAll(".contact").forEach(b=>b.classList.toggle("active",b.dataset.contact===contact));
      renderHistory();
    }
    function addContact(contact){
      contact = contact.trim();
      if(!contact) return;
      if(![...document.querySelectorAll(".contact")].some(b=>b.dataset.contact===contact)){
        contactsEl.insertAdjacentHTML("afterbegin", '<button class="contact" data-contact="'+escapeText(contact)+'" type="button"><span class="avatar">'+escapeText(contact.slice(0,1))+'</span><span class="contactText"><strong>'+escapeText(contact)+'</strong><small>点击选择联系人</small></span></button>');
        bindContacts();
      }
      select(contact);
    }
    function bindContacts(){document.querySelectorAll(".contact").forEach(button=>button.onclick=()=>select(button.dataset.contact))}
    bindContacts();
    addContactEl.addEventListener("keydown", event => { if(event.key==="Enter"){ event.preventDefault(); addContact(addContactEl.value); addContactEl.value=""; }});
    document.getElementById("form").addEventListener("submit", async event => {
      event.preventDefault();
      const contact = (app.dataset.selectedContact || selected || "").trim();
      const text = textEl.value.trim();
      if(!contact || !text){showStatus("联系人和内容不能为空");return}
      sendEl.disabled = true;
      showStatus("正在提交到 Mac relay");
      try{
        const endpoint = mode === "reply" ? "/reply" : "/send";
        const form = new FormData();
        form.set("contact", contact);
        form.set("text", text);
        if(mode === "reply") form.set("token", token); else form.set("secret", secret);
        const response = await fetch(endpoint, {method:"POST", body:form});
        const contentType = response.headers.get("content-type") || "";
        if(!response.ok) throw new Error(contentType.includes("json") ? (await response.json()).error : await response.text());
        textEl.value = "";
        addContact(contact);
        historyItems.unshift({contact, text, createdAt: Date.now(), source: mode});
        renderHistory();
        refreshHistory();
        showStatus("已提交，等待 Mac 微信执行");
      }catch(error){showStatus(error.message || "提交失败")}
      finally{sendEl.disabled = false}
    });
    select(selected);
    refreshHistory();
  </script>
</body>
</html>`, {
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

function errorPage(title, message) {
  return html(
    title,
    `<main>
      <h1>${escapeHtml(title)}</h1>
      <p class="message">${escapeHtml(message)}</p>
      <p class="hint">请从 Bark 通知里的回复链接打开，不要直接打开基础回复页面。</p>
    </main>`,
    400
  );
}


function homePage() {
  return html(
    "BarkBridge Relay",
    `<main>
      <h1>BarkBridge Relay</h1>
      <p class="message">中继服务正在运行。主动发送页面需要带 secret 参数打开；Bark 通知里的回复链接会自动携带 token。</p>
      <p class="hint">可用路径：<br>/chat?secret=你的密钥<br>/compose?secret=你的密钥<br>/control?secret=你的密钥<br>/reply?token=通知令牌<br>/poll?secret=你的密钥&amp;waitMs=0</p>
    </main>`
  );
}


function workerError(error) {
  return Response.json({
    error: String(error && error.message ? error.message : error),
    name: String(error && error.name ? error.name : "Error"),
  }, { status: 500 });
}

function html(title, body, status = 200) {
  return new Response(`<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <style>
    body{margin:0;background:#f3f7f6;color:#17201f;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    main{max-width:560px;margin:0 auto;padding:28px 18px}
    h1{font-size:24px;margin:0 0 14px}
    .message{padding:14px;border:1px solid #d5e4e1;background:#fff;border-radius:8px;line-height:1.5}
    textarea{box-sizing:border-box;width:100%;min-height:150px;margin-top:14px;padding:12px;border:1px solid #c8d8d5;border-radius:8px;font-family:inherit;font-size:18px;line-height:1.45}
    button{width:100%;height:48px;margin-top:12px;border:0;border-radius:8px;background:#007670;color:#fff;font-family:inherit;font-size:16px;font-weight:600}
    .hint{color:#60716e;line-height:1.55}
  </style>
</head>
<body>${body}</body>
</html>`, {
    status,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
