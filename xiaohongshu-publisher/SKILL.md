---
name: xiaohongshu-publisher
description: |
  Publish image-text (图文) posts to Xiaohongshu (小红书) creator platform by controlling a real browser session via Kimi WebBridge or OpenClaw browser tooling. Use when the user asks to post / publish / 发帖 / 发布笔记 to 小红书, automate Xiaohongshu posting, or upload content (images + title + body + topic hashtags) to creator.xiaohongshu.com. Handles the full flow: login-state verification, tab switching (上传图文), multi-image upload via DataTransfer injection, React-friendly title/body filling, real topic (#话题) association through keyboard autocomplete, and anti-automation hardening (randomized delays, hover-before-click, chunk-based input). Always stops before the final 发布 button and waits for explicit user confirmation — NEVER auto-publishes.
---

# Xiaohongshu Publisher

Publish image-text notes to Xiaohongshu's creator platform (`creator.xiaohongshu.com`) through a real logged-in browser. This skill wraps all the DOM quirks and anti-bot workarounds so another agent instance can repeat the flow reliably.

## Hard Rules (read first)

1. **Never press the 发布 (publish) button without explicit user confirmation in the same turn.** Always stop, screenshot the filled form, and ask.
2. **All images must live inside the agent workspace** so the browser's `mediaLocalRoots` check passes. Copy to `/Users/<user>/.openclaw/workspace/...` first if they're elsewhere.
3. **If a captcha (slider / click-picture) or login prompt appears, stop immediately, screenshot, and hand off to the user.** Do not retry or brute-force — that's what gets accounts flagged.
4. **Respect content authenticity.** Confirm title/body/images with the user before filling. This skill executes; the human authorizes.

## Prerequisites

- A Chromium browser (Chrome/Edge) running on the host with the user already logged in to Xiaohongshu web (`www.xiaohongshu.com` or `creator.xiaohongshu.com`).
- Kimi WebBridge daemon healthy: `~/.kimi-webbridge/bin/kimi-webbridge status` reports `running:true` and `extension_connected:true`. If unhealthy, read `references/operations.md` of the `kimi-webbridge` skill — do not try to fix in this skill.
- Images prepared: 1–18 JPG/PNG/WEBP files, each ≤ 32 MB. 3:4 aspect ratio recommended. No GIF/live photos.

## Standard Workflow

All curl/JS snippets assume WebBridge on `127.0.0.1:10086` and session `xhs`. See `references/browser-calls.md` for the raw command patterns.

### Step 1 — Open the publish page

```bash
curl -s -X POST http://127.0.0.1:10086/command \
  -H 'Content-Type: application/json' \
  -d '{"action":"navigate","args":{"url":"https://creator.xiaohongshu.com/publish/publish?source=official","newTab":true},"session":"xhs"}'
```

Then screenshot with the helper script and verify:
- Top-right shows the expected account avatar/name (login state OK)
- Three tabs visible: `上传视频 | 上传图文 | 写长文`

If login missing → hand off to user.

### Step 2 — Switch to "上传图文"

The tabs are `<div>` elements, not `<button>` — query by text content:

```js
(() => {
  const tab = [...document.querySelectorAll("div,span,button")]
    .find(e => e.innerText === "上传图文" && e.offsetParent);
  if (!tab) return "not found";
  const r = tab.getBoundingClientRect();
  tab.dispatchEvent(new MouseEvent("mouseover", {bubbles:true, clientX:r.x+r.width/2, clientY:r.y+r.height/2}));
  return "hover ok";
})()
```

`sleep 1.3` → then `tab.click()` in a separate call. Two-step hover+click is the anti-bot baseline for the whole skill.

### Step 3 — Upload images (the tricky part)

The XHS page has a visible `<input type=file accept=".jpg,.jpeg,.png,.webp" multiple>`. The WebBridge `upload` action is rejected by Chrome DevTools (`Not allowed`) because of CDP restrictions on the file dialog. **Workaround: build a `DataTransfer` in the page, assign `input.files`, dispatch `change`.**

Use `scripts/xhs_upload_images.py`:

```bash
python3 scripts/xhs_upload_images.py \
  /path/to/img1.png \
  /path/to/img2.png \
  /path/to/img3.png
```

The script:
1. Tags the file input with `data-ai-upload="1"` so subsequent calls are stable.
2. Initializes `window.__xhsUploadDT = new DataTransfer()` once.
3. For each file: base64 → atob → Uint8Array → `new File(...)` → `DT.items.add(f)`. **One file per request** (large base64 payloads break single-shot curl `-d`; script uses `--data-binary @-` via stdin).
4. Final call: `input.files = DT.files; input.dispatchEvent(new Event('change', {bubbles:true}))`.
5. Wait ~5s; screenshot to confirm thumbnails + `图片编辑 N/18` counter.

### Step 4 — Fill title

**DO NOT** use `inputs[0]` — the file input is usually index 0. Locate by placeholder:

```js
const i = [...document.querySelectorAll('input')]
  .find(e => e.placeholder && e.placeholder.includes('标题'));
```

Small Red Book uses React; plain `input.value = '…'` won't register. Use the native setter trick:

```js
const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
setter.call(input, titleText);
input.dispatchEvent(new Event('input', {bubbles:true}));
input.dispatchEvent(new Event('change', {bubbles:true}));
```

Keep title ≤ 20 Chinese chars (XHS enforces). Setting the full string at once is fine — XHS does not rate-limit title input.

### Step 5 — Fill body

Body is a contenteditable `<div>` (Tiptap editor). The reliable insertion method is `document.execCommand('insertText')` after placing the caret at the end:

```js
const d = [...document.querySelectorAll('div[contenteditable=true]')].find(e => e.offsetParent);
d.setAttribute('data-ai-body','1');  // stable handle for later
d.focus();
const sel = window.getSelection();
const r = document.createRange();
r.selectNodeContents(d); r.collapse(false);
sel.removeAllRanges(); sel.addRange(r);
document.execCommand('insertText', false, bodyText);
```

**Known rendering quirk**: keycap emoji (1️⃣ 2️⃣ 3️⃣) may display as plain boxed digits in XHS web preview. They render correctly on mobile app. If the user wants identical web/app rendering, substitute with ①②③ or 1. 2. 3.

### Step 6 — Add topic hashtags (real links, not plain text)

This is the single most important quality step. A real topic has a `<a class="tiptap-topic" data-topic="{…}">` with an id + link. Plain `#text` does nothing for discoverability.

To get the real topic chip, simulate: type `#` → type chars → wait for autocomplete dropdown → press Enter to select the first suggestion.

Use `scripts/xhs_add_topics.py`:

```bash
python3 scripts/xhs_add_topics.py "AI产品经理" "女生做产品" "AI" "产品经理日常" "转行AI"
```

The script per tag:
1. `execCommand('insertText', false, '#')` at body end.
2. Loop characters with 50–120ms random delay, each via `execCommand('insertText', …)`.
3. Sleep 1.2s for autocomplete to populate.
4. Dispatch `KeyboardEvent('keydown'|'keyup', {key:'Enter', keyCode:13, bubbles:true})` on the body div to accept suggestion.
5. Space separator + random 0.3–0.6s gap before next tag.

Verify after: query `document.querySelectorAll('.tiptap-topic').length` should equal the tag count.

### Step 7 — Preview and hand off

1. Screenshot the full editor (scroll the body div to its bottom via `d.scrollIntoView({block:'center'})` or `d.scrollTop = d.scrollHeight` — page-level scroll does NOT move the XHS editor).
2. Send the screenshot to the user with a bullet summary: title ✓, body char count ✓, image count ✓, topic count ✓.
3. Ask explicitly: "发 / 改 / 存草稿?" Wait for the reply.

### Step 8 — Publish (only on explicit "发")

```js
const btn = [...document.querySelectorAll("button")].find(b => b.innerText.trim() === "发布" && b.offsetParent);
// hover first
const r = btn.getBoundingClientRect();
btn.dispatchEvent(new MouseEvent("mouseover", {bubbles:true, clientX:r.x+r.width/2, clientY:r.y+r.height/2}));
// sleep 1.4s in shell, then:
btn.click();
```

Wait 5s → screenshot. Success indicators:
- URL redirects back to `/publish/publish` empty state, OR
- Creator notemanage page shows a new row with the title and `发布于 <timestamp>`.

Confirm by navigating to `https://creator.xiaohongshu.com/creator/notemanage` and looking for the new entry under `全部笔记(N)`.

## Anti-Automation Playbook

| Technique | Why |
|---|---|
| Random delays 0.3–1.5s between DOM ops | Uniform timing is a known bot signal |
| `mouseover` before `click` | Real users hover; bots teleport-click |
| Character-by-character body/topic typing | Burst-inserts on Tiptap look scripted |
| Reuse existing tab (`newTab: false` after first) | Repeated `window.open` spikes look botty |
| Never drag-and-drop; always native `<input type=file>` | Drag events are the easiest automation tell |
| Publish during real-user active hours (12–13:30, 19–22) | Off-hour batches trigger risk scoring |
| No more than 1 post per session without manual browsing in between | See `references/warming.md` |

## When Things Go Wrong

- **Captcha appears** → screenshot, hand off, stop. Never click through.
- **"请登录" redirect** → token expired. Tell the user to log in manually, abort.
- **`upload` returns `Not allowed`** → expected; use the DataTransfer script instead.
- **Topics stay as plain `#text`** → autocomplete didn't populate. Increase wait to 2s; confirm network isn't throttled; check that body div has focus before sending Enter.
- **Only partial body shows in screenshot** → the editor scroll is internal. Use `d.scrollTop = d.scrollHeight` on the body div, not `window.scrollTo`.
- **Images upload succeeds but preview empty** → you set `files` on the wrong input. Confirm `input[type=file][accept*=".png"]` and that `data-ai-upload="1"` is present only on the intended one.

## References

- `references/browser-calls.md` — Raw WebBridge curl patterns for every step
- `references/warming.md` — Account warming + posting cadence guidance
- `scripts/xhs_upload_images.py` — Multi-image DataTransfer injector
- `scripts/xhs_add_topics.py` — Topic hashtag autocomplete simulator
- `scripts/xhs_fill_form.py` — Title + body filler (React native-setter + execCommand)
