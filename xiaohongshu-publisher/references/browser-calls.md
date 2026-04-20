# Browser Calls Reference

Raw WebBridge curl patterns for every step of the Xiaohongshu publish flow. Copy-paste friendly.

## Daemon convention

- Endpoint: `http://127.0.0.1:10086/command`
- Session: `"xhs"` for the creator flow, separate session if you also need to read feed
- All requests use `POST` with `Content-Type: application/json`
- For payloads with large base64 (images), use `--data-binary @-` over stdin, not `-d '…'` (you will hit `Argument list too long`)

## Health check

```bash
~/.kimi-webbridge/bin/kimi-webbridge status
```

Expect `running: true` and `extension_connected: true`. Anything else → read the kimi-webbridge skill's `references/operations.md`.

## 1. Open the publish page

```bash
curl -s -X POST http://127.0.0.1:10086/command \
  -H 'Content-Type: application/json' \
  -d '{"action":"navigate","args":{"url":"https://creator.xiaohongshu.com/publish/publish?source=official","newTab":true},"session":"xhs"}'
```

Subsequent navigations in the same flow should use `newTab:false` to avoid opening many windows (bot signal).

## 2. Screenshot helper

Never call screenshot API directly. Use:

```bash
bash ~/.agents/skills/kimi-webbridge/scripts/screenshot.sh -s xhs -o /path/to/out.png
```

## 3. Click the "上传图文" tab

Tabs are plain `<div>`, not buttons. Two-step hover+click:

```bash
# hover
curl -s -X POST http://127.0.0.1:10086/command -H 'Content-Type: application/json' -d '{
  "action":"evaluate",
  "args":{"code":"(()=>{const t=[...document.querySelectorAll(\"div,span,button\")].find(e=>e.innerText===\"上传图文\"&&e.offsetParent);if(!t)return\"no\";const r=t.getBoundingClientRect();t.dispatchEvent(new MouseEvent(\"mouseover\",{bubbles:true,clientX:r.x+r.width/2,clientY:r.y+r.height/2}));return\"hover\"})()"},
  "session":"xhs"
}'
sleep 1.3
# click
curl -s -X POST http://127.0.0.1:10086/command -H 'Content-Type: application/json' -d '{
  "action":"evaluate",
  "args":{"code":"(()=>{const t=[...document.querySelectorAll(\"div,span,button\")].find(e=>e.innerText===\"上传图文\"&&e.offsetParent);t.click();return\"clicked\"})()"},
  "session":"xhs"
}'
```

## 4. Tag the file input (for stable lookups)

```bash
curl -s -X POST http://127.0.0.1:10086/command -H 'Content-Type: application/json' -d '{
  "action":"evaluate",
  "args":{"code":"(()=>{const i=document.querySelector(\"input[type=file][accept*=\\\".png\\\"]\");i.setAttribute(\"data-ai-upload\",\"1\");return\"tagged\"})()"},
  "session":"xhs"
}'
```

## 5. Upload images

Do NOT use the WebBridge `upload` action — it fails with `Not allowed` (CDP restriction).

Use the DataTransfer injection pattern in `scripts/xhs_upload_images.py`. The script:

1. Creates `window.__xhsUploadDT = new DataTransfer()`
2. For each file, reads its base64 and constructs `new File(Uint8Array, name)` inside the page, then `DT.items.add(f)`
3. Assigns `input.files = DT.files` and dispatches `change`

Command:

```bash
python3 scripts/xhs_upload_images.py img1.png img2.png img3.png
```

## 6. Locate title and body

Title input is NOT index 0 (file inputs occupy the early indices). Locate by placeholder:

```js
const title = [...document.querySelectorAll('input')]
  .find(e => e.placeholder && e.placeholder.includes('标题'));
```

Body is a Tiptap contenteditable div:

```js
const body = [...document.querySelectorAll('div[contenteditable=true]')]
  .find(e => e.offsetParent);
body.setAttribute('data-ai-body', '1');
```

## 7. Fill title (React native setter)

```js
const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
setter.call(title, titleText);
title.dispatchEvent(new Event('input',  {bubbles:true}));
title.dispatchEvent(new Event('change', {bubbles:true}));
```

Plain `title.value = x` will NOT register. React tracks its own mirror via the prototype setter.

## 8. Fill body (execCommand insertText)

```js
body.focus();
const sel = window.getSelection();
const r = document.createRange();
r.selectNodeContents(body);
r.collapse(false);
sel.removeAllRanges();
sel.addRange(r);
document.execCommand('insertText', false, bodyText);
```

Keycap emoji (1️⃣ 2️⃣ 3️⃣) will render as plain boxed digits on XHS web preview but render correctly on mobile app. If the user wants identical rendering in both, substitute with ①②③.

## 9. Add a single topic hashtag

Per tag:

```js
// 1) # character
document.execCommand('insertText', false, '#');
// sleep 500-900ms
// 2) name characters, each with 50-120ms random delay
for (const ch of tagName) {
  document.execCommand('insertText', false, ch);
  // sleep 50-120ms
}
// sleep 1200ms for autocomplete to populate
// 3) Enter to accept first suggestion
const d = document.querySelector('div[data-ai-body]');
d.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true, cancelable:true}));
d.dispatchEvent(new KeyboardEvent('keyup',   {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true, cancelable:true}));
// sleep 800-1300ms
// 4) trailing space
document.execCommand('insertText', false, ' ');
```

Verify: `document.querySelectorAll('.tiptap-topic').length === expectedCount`.

## 10. Scrolling the editor preview

Page-level scrolling does NOT move the XHS editor. The body div has its own overflow:

```js
const d = document.querySelector('div[data-ai-body]');
d.scrollTop = d.scrollHeight;
```

To scroll a specific element into view:

```js
someElement.scrollIntoView({block: 'center'});
```

## 11. Publish button (handoff to user required)

```js
const btn = [...document.querySelectorAll('button')]
  .find(b => b.innerText.trim() === '发布' && b.offsetParent);
const r = btn.getBoundingClientRect();
// hover first
btn.dispatchEvent(new MouseEvent('mouseover', {bubbles:true, clientX:r.x+r.width/2, clientY:r.y+r.height/2}));
// sleep 1.4s in shell
btn.click();
```

DO NOT automate this step without explicit user approval in the current turn.

## 12. Post-publish verification

Check notemanage page:

```bash
curl -s -X POST http://127.0.0.1:10086/command -H 'Content-Type: application/json' -d '{
  "action":"navigate",
  "args":{"url":"https://creator.xiaohongshu.com/creator/notemanage","newTab":false},
  "session":"xhs"
}'
```

Look for a new row matching the title under `全部笔记(N)`.

## 13. Commenting on another user's post

Web-only evaluate pattern (no script yet; codify if this becomes a repeated workflow):

```js
// Open the comment area's contenteditable
const p = document.querySelector('p.content-input');
p.focus();
// Insert full comment text
document.execCommand('insertText', false, commentText);
// Submit button
const submit = document.querySelector('button.btn.submit');
submit.click();
```

Caveats:
- `p.content-input` is a real contenteditable inside a collapsed UI. Clicks on outer containers (`.inner-when-not-active`, `.input-box`, `.content-edit`) often do nothing because of pointer-events shenanigans. `p.focus()` + `execCommand` works without visible UI expansion.
- **XHS web does NOT expose edit/delete for your own comments.** Only mobile app allows editing within ~2 min. If a comment needs to be changed, hand off to the user's phone.
- Always run a sensitive-content pre-flight review before submitting. See SKILL.md "Hard Rules".
