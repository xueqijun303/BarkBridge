#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description="Poll BarkBridge relay and send replies through Mac WeChat.")
    parser.add_argument("--poll-url", required=True, help="Relay poll URL, including secret query string.")
    parser.add_argument("--interval", type=int, default=1, help="Delay after each poll in seconds.")
    parser.add_argument("--once", action="store_true", help="Poll once and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print replies without operating WeChat.")
    args = parser.parse_args()

    while True:
        try:
            replies = fetch_replies(args.poll_url)
            for reply in replies:
                contact = str(reply.get("contact") or "").strip()
                text = str(reply.get("text") or "").strip()
                if not contact or not text:
                    print(f"skip invalid reply: {reply}", flush=True)
                    continue
                print(f"picked: {contact}: {text[:40]}", flush=True)
                if args.dry_run:
                    print(f"dry-run: {contact}: {text}", flush=True)
                else:
                    send_wechat(contact, text)
                    print(f"sent: {contact}", flush=True)
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
