#!/usr/bin/env python3
"""
xhs_fill_form.py — Fill Xiaohongshu note title + body.

Usage:
    python3 xhs_fill_form.py --title "<title text>" --body-file /path/to/body.txt

The body file is read as UTF-8. Use LF newlines. Emoji are preserved.

Caveats covered inside:
    - Small Red Book uses React; plain .value= won't notify the store. Native setter + 'input'/'change' events are required.
    - Body is a Tiptap contenteditable div. document.execCommand('insertText') is the most reliable path.
    - After filling, the body div is tagged with data-ai-body="1" so xhs_add_topics.py can find it.
"""
import argparse, json, subprocess, time

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


def fill_title(title):
    # Focus the title input by placeholder match
    print('focus title:', run(
        "(() => {"
        "const i = [...document.querySelectorAll('input')].find(e => e.placeholder && e.placeholder.includes('标题'));"
        "if (!i) return 'no title input';"
        "i.focus();"
        "return 'ok';"
        "})()"
    ))
    time.sleep(0.6)
    code = (
        "(() => {"
        "const i = [...document.querySelectorAll('input')].find(e => e.placeholder && e.placeholder.includes('标题'));"
        "const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;"
        f"setter.call(i, {json.dumps(title)});"
        "i.dispatchEvent(new Event('input', {bubbles: true}));"
        "i.dispatchEvent(new Event('change', {bubbles: true}));"
        "return 'title:' + i.value;"
        "})()"
    )
    print('set title:', run(code)[:200])


def fill_body(text):
    # Tag + focus the body div
    print('locate body:', run(
        "(() => {"
        "const d = [...document.querySelectorAll('div[contenteditable=true]')].find(e => e.offsetParent);"
        "if (!d) return 'no body';"
        "d.focus();"
        "d.setAttribute('data-ai-body', '1');"
        "return 'tagged';"
        "})()"
    ))
    time.sleep(0.8)
    code = (
        "(() => {"
        "const d = document.querySelector('div[data-ai-body]');"
        "d.focus();"
        "const sel = window.getSelection();"
        "const r = document.createRange();"
        "r.selectNodeContents(d); r.collapse(false);"
        "sel.removeAllRanges(); sel.addRange(r);"
        f"const ok = document.execCommand('insertText', false, {json.dumps(text)});"
        "return 'inserted:' + ok + '|len:' + d.innerText.length;"
        "})()"
    )
    print('insert body:', run(code)[:200])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--title', required=True)
    ap.add_argument('--body-file', required=True)
    args = ap.parse_args()

    body_text = open(args.body_file, 'r', encoding='utf-8').read().rstrip('\n')
    fill_title(args.title)
    time.sleep(1.2)
    fill_body(body_text)


if __name__ == '__main__':
    main()
