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
      this.enqueue(reply);
      return Response.json({ ok: true });
    }
    if (url.pathname === "/dequeue" && request.method === "GET") {
      if (this.queue.length > 0) {
        return Response.json({ replies: this.queue.splice(0, this.queue.length) });
      }
      return this.waitForReply();
    }
    return new Response("Not found", { status: 404 });
  }

  enqueue(reply) {
    this.pruneWaiters();
    const waiter = this.waiters.shift();
    if (waiter) {
      clearTimeout(waiter.timer);
      waiter.resolve(Response.json({ replies: [reply] }));
      return;
    }
    this.queue.push(reply);
    while (this.queue.length > 200) this.queue.shift();
  }

  waitForReply() {
    return new Promise((resolve) => {
      const waiter = {
        resolve,
        expiresAt: Date.now() + 25000,
      };
      waiter.timer = setTimeout(() => {
        const index = this.waiters.indexOf(waiter);
        if (index >= 0) this.waiters.splice(index, 1);
        resolve(Response.json({ replies: [] }));
      }, 25000);
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

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/reply" && request.method === "GET") {
      return replyPage(url);
    }
    if (url.pathname === "/reply" && request.method === "POST") {
      return saveReply(request, env);
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
      body: JSON.stringify({ id, token, contact, text, createdAt: Date.now() }),
      headers: { "content-type": "application/json" },
    });
    return html("Reply saved", "<main><h1>Reply saved</h1><p>You can close this page.</p></main>");
  } catch (error) {
    return workerError(error);
  }
}

async function pollReplies(url, env) {
  if (env.REPLY_SECRET && url.searchParams.get("secret") !== env.REPLY_SECRET) {
    return Response.json({ replies: [] }, { status: 403 });
  }

  try {
    return await relayStub(env).fetch("https://relay.local/dequeue");
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
  return html(
    "BarkBridge Reply",
    `<main>
      <h1>${contact}</h1>
      <p class="message">${message}</p>
      <form method="post" action="/reply">
        <input type="hidden" name="token" value="${token}">
        <input type="hidden" name="contact" value="${contact}">
        <textarea name="text" autofocus placeholder="Type reply..." required></textarea>
        <button type="submit">Send to Mac</button>
      </form>
    </main>`
  );
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
    textarea{box-sizing:border-box;width:100%;min-height:150px;margin-top:14px;padding:12px;border:1px solid #c8d8d5;border-radius:8px;font:16px inherit}
    button{width:100%;height:48px;margin-top:12px;border:0;border-radius:8px;background:#007670;color:#fff;font:600 16px inherit}
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
