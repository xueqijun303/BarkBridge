#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.error
import urllib.request

PENDING_PATH = os.path.expanduser("~/.barkbridge/pending_replies.json")


def main():
    parser = argparse.ArgumentParser(description="Poll BarkBridge relay and send replies through Mac WeChat.")
    parser.add_argument("--poll-url", required=True, help="Relay poll URL, including secret query string.")
    parser.add_argument("--interval", type=int, default=1, help="Delay after each poll in seconds.")
    parser.add_argument("--receipt-url", default=os.environ.get("BARKBRIDGE_RECEIPT_URL", ""), help="Optional Bark endpoint URL for send receipts, for example https://api.day.app/key.")
    parser.add_argument("--max-retries", type=int, default=5, help="Maximum local retry attempts for failed sends.")
    parser.add_argument("--once", action="store_true", help="Poll once and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print replies without operating WeChat.")
    args = parser.parse_args()

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
        try:
            send_wechat(contact, text)
            print(f"sent: {contact}", flush=True)
            send_receipt(args.receipt_url, "BarkBridge 回复成功", f"已通过 Mac 微信回复: {contact}")
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


def send_wechat(contact, text):
    script = r'''
on run argv
  set contactName to item 1 of argv
  set replyText to item 2 of argv

  tell application "WeChat" to activate
  delay 1

  tell application "System Events"
    tell process "WeChat"
      set frontmost to true
      click menu item "搜索" of menu 1 of menu bar item "编辑" of menu bar 1
    end tell
    delay 0.5

    set the clipboard to contactName
    keystroke "v" using command down
    delay 1.2
    key code 36
    delay 1

    set the clipboard to replyText
    keystroke "v" using command down
    delay 0.4
    key code 36
  end tell
end run
'''
    osascript_bin = "/Applications/BarkBridgeOsascript.app/Contents/MacOS/BarkBridgeOsascript"
    if not os.path.exists(osascript_bin):
        osascript_bin = "/usr/bin/osascript"
    subprocess.run([osascript_bin, "-e", script, contact, text], check=True, timeout=20)


if __name__ == "__main__":
    main()
