#!/usr/bin/env python3
import argparse
import os
import time


DEFAULT_ROOT = os.path.expanduser("~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files")


def snapshot(root):
    rows = {}
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            rows[path] = (st.st_mtime, st.st_size)
    return rows


def interesting(path):
    lower = path.lower()
    markers = (
        "/msg/",
        "/message/",
        "/db_storage/message/",
        "/cache/",
        "/temp/",
        "voice",
        "audio",
        "media",
        "attach",
        "bubble",
        ".amr",
        ".silk",
        ".aud",
        ".wav",
        ".mp3",
        ".m4a",
        ".dat",
    )
    return any(marker in lower for marker in markers)


def main():
    parser = argparse.ArgumentParser(description="Watch Mac WeChat data files changed by a new voice message.")
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--all", action="store_true", help="Show all changed files instead of likely message/media files only.")
    args = parser.parse_args()

    root = os.path.expanduser(args.root)
    if not os.path.isdir(root):
        raise SystemExit(f"missing WeChat data root: {root}")

    before = snapshot(root)
    print(f"watching {root}")
    print("现在请让微信收到一条新的语音消息，或在 Mac 微信里点开/转文字一条语音。")
    deadline = time.time() + max(5, args.seconds)
    seen = set()
    while time.time() < deadline:
        time.sleep(1)
        after = snapshot(root)
        changed = []
        for path, meta in after.items():
            old = before.get(path)
            if old != meta and path not in seen and (args.all or interesting(path)):
                changed.append((meta[0], meta[1], path, old))
                seen.add(path)
        for mtime, size, path, old in sorted(changed):
            old_size = "-" if old is None else str(old[1])
            print(f"{time.strftime('%H:%M:%S', time.localtime(mtime))} size {old_size}->{size} {path}", flush=True)
    print("done")


if __name__ == "__main__":
    main()
