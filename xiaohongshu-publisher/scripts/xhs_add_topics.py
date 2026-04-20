#!/usr/bin/env python3
"""
xhs_add_topics.py — Add topic hashtags to Xiaohongshu note body by simulating
# -> chars -> Enter (accept autocomplete) flow. Produces real <a class="tiptap-topic">
links with topic id + URL, not just plain "#text".

Usage:
    python3 xhs_add_topics.py "AI产品经理" "女生做产品" ...

Prerequisites:
    - Body div tagged with data-ai-body="1" (done by xhs_fill_form.py)
    - Daemon + session 'xhs' as usual
"""
import json, subprocess, sys, time, random

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


def focus_end():
    return run(
        "(() => {"
        "const d = document.querySelector('div[data-ai-body]');"
        "if (!d) return 'no body';"
        "d.focus();"
        "const sel = window.getSelection();"
        "const r = document.createRange();"
        "r.selectNodeContents(d); r.collapse(false);"
        "sel.removeAllRanges(); sel.addRange(r);"
        "return 'focused';"
        "})()"
    )


def insert_text(text):
    return run(f"document.execCommand('insertText', false, {json.dumps(text)})")


def press_enter_on_body():
    # Tiptap topic suggestion listens for real KeyboardEvents with keyCode 13
    return run(
        "(() => {"
        "const d = document.querySelector('div[data-ai-body]');"
        "d.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true, cancelable:true}));"
        "d.dispatchEvent(new KeyboardEvent('keyup',   {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true, cancelable:true}));"
        "return 'enter';"
        "})()"
    )


def main(tags):
    print('focus:', focus_end())
    time.sleep(0.8)
    # leading separator so tags don't fuse with trailing body text
    insert_text('\n\n')
    time.sleep(0.5)

    for tag in tags:
        print(f'[{tag}] #:', insert_text('#'))
        time.sleep(random.uniform(0.5, 0.9))
        for ch in tag:
            insert_text(ch)
            time.sleep(random.uniform(0.05, 0.12))
        # wait for autocomplete dropdown
        time.sleep(1.3)
        print(f'[{tag}] enter:', press_enter_on_body())
        time.sleep(random.uniform(0.8, 1.3))
        insert_text(' ')
        time.sleep(random.uniform(0.3, 0.6))

    # verify
    count = run(
        "(() => document.querySelectorAll('.tiptap-topic').length)()"
    )
    print('tiptap-topic count:', count)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: xhs_add_topics.py "tag1" "tag2" ...', file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1:])
