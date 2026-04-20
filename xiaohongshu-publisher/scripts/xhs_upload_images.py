#!/usr/bin/env python3
"""
xhs_upload_images.py — Inject 1..N local images into the Xiaohongshu file input
via DataTransfer, bypassing Chrome DevTools' 'Not allowed' error on upload.

Usage:
    python3 xhs_upload_images.py <file1> [file2] ... [fileN]

Assumes:
    - Kimi WebBridge daemon running at 127.0.0.1:10086
    - Session name 'xhs'
    - Current tab is on https://creator.xiaohongshu.com/publish/publish
      with the "上传图文" tab active (so an input[type=file][accept*=".png"] exists)
"""
import json, base64, subprocess, sys, os

DAEMON = 'http://127.0.0.1:10086/command'
SESSION = 'xhs'


def run(code):
    body = json.dumps({'action': 'evaluate', 'args': {'code': code}, 'session': SESSION})
    r = subprocess.run(
        ['curl', '-s', '-X', 'POST', DAEMON,
         '-H', 'Content-Type: application/json',
         '--data-binary', '@-'],
        input=body, capture_output=True, text=True,
    )
    return r.stdout.strip()


def main(paths):
    for p in paths:
        if not os.path.isfile(p):
            print(f'ERROR: not a file: {p}', file=sys.stderr)
            sys.exit(1)

    # 1) Tag the file input for stable selection
    tag = run(
        "(() => {"
        "const i = document.querySelector('input[type=file][accept*=\".png\"], input[type=file][accept*=\".jpg\"]');"
        "if (!i) return 'no file input';"
        "i.setAttribute('data-ai-upload', '1');"
        "return 'tagged';"
        "})()"
    )
    print('tag input:', tag)

    # 2) Init DataTransfer on window
    print('init DT:', run("window.__xhsUploadDT = new DataTransfer(); 'ok'"))

    # 3) Push each file in its own request (base64 payload would overflow single-shot curl -d)
    for idx, path in enumerate(paths, 1):
        b64 = base64.b64encode(open(path, 'rb').read()).decode()
        name = os.path.basename(path)
        code = (
            "(() => {"
            f"const b64 = '{b64}';"
            "const bin = atob(b64);"
            "const bytes = new Uint8Array(bin.length);"
            "for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);"
            f"const f = new File([bytes], '{name}', {{type: 'image/png'}});"
            "window.__xhsUploadDT.items.add(f);"
            "return 'added:' + window.__xhsUploadDT.files.length;"
            "})()"
        )
        print(f'  [{idx}/{len(paths)}] {name}:', run(code)[:200])

    # 4) Assign + dispatch change
    final = run(
        "(() => {"
        "const i = document.querySelector('input[data-ai-upload=\"1\"]');"
        "if (!i) return 'input missing';"
        "i.files = window.__xhsUploadDT.files;"
        "i.dispatchEvent(new Event('change', {bubbles: true}));"
        "return 'dispatched:' + i.files.length;"
        "})()"
    )
    print('dispatch:', final)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: xhs_upload_images.py <file1> [file2] ...', file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1:])
