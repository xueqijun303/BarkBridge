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

async function saveReply(request, env) {
  if (!env.REPLIES) return new Response("KV binding REPLIES is missing", { status: 500 });
  const form = await request.formData();
  const token = String(form.get("token") || "").trim();
  const text = String(form.get("text") || "").trim();
  if (!token || !text) return new Response("Missing token or text", { status: 400 });

  const id = `${Date.now()}-${crypto.randomUUID()}`;
  await env.REPLIES.put(`reply:${id}`, JSON.stringify({ id, token, text }), {
    expirationTtl: 3600,
  });
  return html("Reply saved", "<main><h1>Reply saved</h1><p>You can close this page.</p></main>");
}

async function pollReplies(url, env) {
  if (!env.REPLIES) return Response.json({ replies: [] }, { status: 500 });
  if (env.REPLY_SECRET && url.searchParams.get("secret") !== env.REPLY_SECRET) {
    return Response.json({ replies: [] }, { status: 403 });
  }

  const list = await env.REPLIES.list({ prefix: "reply:", limit: 50 });
  const replies = [];
  for (const key of list.keys) {
    const raw = await env.REPLIES.get(key.name);
    if (raw) replies.push(JSON.parse(raw));
    await env.REPLIES.delete(key.name);
  }
  return Response.json({ replies });
}

function replyPage(url) {
  const token = escapeHtml(url.searchParams.get("token") || "");
  const contact = escapeHtml(url.searchParams.get("contact") || "WeChat");
  const message = escapeHtml(url.searchParams.get("message") || "");
  return html(
    "BarkBridge Reply",
    `<main>
      <h1>${contact}</h1>
      <p class="message">${message}</p>
      <form method="post" action="/reply">
        <input type="hidden" name="token" value="${token}">
        <textarea name="text" autofocus placeholder="Type reply..." required></textarea>
        <button type="submit">Send to Android</button>
      </form>
    </main>`
  );
}

function html(title, body) {
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
  </style>
</head>
<body>${body}</body>
</html>`, {
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
