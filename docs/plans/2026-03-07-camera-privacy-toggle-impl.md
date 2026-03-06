# Camera Privacy Toggle — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add in-bar camera toggle, green active indicator, persistent "Stop Camera" button, and 60-second video toast nudge — so camera is always user-controlled and visibly indicated.

**Architecture:** All changes are in `chrome-extension/content.js` (UI + logic) and `chrome-extension/options.html` (label only). No backend changes. The `attentionMonitoring` storage key becomes a feature gate (shows/hides camera button) rather than an auto-start trigger. A new `_cameraEnabled` runtime boolean tracks the in-session camera state separately.

**Tech Stack:** Chrome Extension MV3, Shadow DOM, vanilla JS, CSS animations, `chrome.storage.sync`

---

### Task 1: Add CSS for camera button, green indicator, stop-camera button, and toast

**Files:**
- Modify: `chrome-extension/content.js:57-267` (the `styleEl.textContent = \`` block)

**Step 1: Locate the style block**

Open `chrome-extension/content.js`. Find the `styleEl.textContent = \`` block that starts around line 57 and ends around line 267 (just before `shadow.appendChild(styleEl)`).

**Step 2: Add new CSS rules**

Inside that template literal, add the following CSS at the very end, just before the closing backtick (around line 266, after the `pulse-red` keyframe block):

```css
    /* ── Camera toggle button ── */
    #eale-camera-btn {
      background: rgba(255,255,255,0.12);
      color: #e2e8f0;
      border: 1.5px solid rgba(255,255,255,0.2);
      border-radius: 24px;
      padding: 8px 13px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: background .15s, border-color .15s;
      white-space: nowrap;
    }
    #eale-camera-btn:hover { background: rgba(255,255,255,0.18); border-color: rgba(255,255,255,0.32); }
    #eale-camera-btn.cam-on {
      background: #15803d;
      border-color: #16a34a;
      color: #fff;
      box-shadow: 0 4px 12px rgba(21,128,61,.45);
    }
    #eale-camera-btn.cam-on:hover { background: #166534; }

    /* Green indicator dot (macOS-style) */
    .cam-indicator {
      width: 8px; height: 8px; border-radius: 50%;
      background: #4ade80;
      animation: pulse-green 2s infinite;
      display: none;
    }
    .cam-on .cam-indicator { display: inline-block; }
    @keyframes pulse-green {
      0%,100% { opacity:1; box-shadow: 0 0 0 0 rgba(74,222,128,.6); }
      50%      { opacity:.85; box-shadow: 0 0 0 4px rgba(74,222,128,0); }
    }

    /* Stop Camera button */
    #eale-stop-camera-btn {
      background: #dc2626;
      color: #fff;
      border: none;
      border-radius: 24px;
      padding: 8px 13px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      display: none;
      align-items: center;
      gap: 4px;
      box-shadow: 0 4px 12px rgba(220,38,38,.4);
      transition: background .15s;
      white-space: nowrap;
    }
    #eale-stop-camera-btn.visible { display: flex; }
    #eale-stop-camera-btn:hover { background: #b91c1c; }

    /* Camera nudge toast */
    #eale-cam-toast {
      background: #1e1b4b;
      border: 1.5px solid #4f46e5;
      border-radius: 12px;
      padding: 10px 14px;
      display: none;
      align-items: center;
      gap: 10px;
      box-shadow: 0 6px 20px rgba(79,70,229,.35);
      animation: slideUp .2s ease;
      max-width: 340px;
    }
    #eale-cam-toast.visible { display: flex; }
    .toast-text { font-size: 12px; color: #e0e7ff; flex: 1; line-height: 1.4; }
    .toast-cam-on-btn {
      background: #4f46e5; color: #fff; border: none; border-radius: 7px;
      padding: 6px 11px; font-size: 12px; font-weight: 700; cursor: pointer;
      white-space: nowrap; transition: background .12s;
    }
    .toast-cam-on-btn:hover { background: #4338ca; }
    .toast-dismiss-btn {
      background: none; border: none; color: #94a3b8; cursor: pointer;
      font-size: 16px; line-height: 1; padding: 0 2px;
    }
    .toast-dismiss-btn:hover { color: #e0e7ff; }
```

**Step 3: Manually verify**

Reload the extension at `chrome://extensions`, open any allowed page (e.g. `localhost`), open DevTools → Elements → find `#eale-shadow-host` → check shadow root for the new CSS rules. No errors expected.

**Step 4: Commit**

```bash
git add chrome-extension/content.js
git commit -m "style: add camera toggle, indicator, stop button, and toast CSS"
```

---

### Task 2: Add camera toggle button, stop-camera button, and toast element to the DOM

**Files:**
- Modify: `chrome-extension/content.js` — the "Build UI" section (~line 306-336)

**Step 1: Locate the button row setup**

Find this block (around line 308-331):
```js
  // Floating buttons row
  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:6px;align-items:center;justify-content:flex-end;";

  const btn = document.createElement("button");
  btn.id = "eale-btn";
  btn.innerHTML = `<span class="dot"></span> EALE Check`;

  const learnBtn = document.createElement("button");
  learnBtn.id = "eale-learn-floating";
  // ...

  btnRow.appendChild(learnBtn);
  btnRow.appendChild(btn);
  container.appendChild(btnRow);

  // Panel
  const panel = document.createElement("div");
  panel.id = "eale-panel";
  container.insertBefore(panel, btnRow);
```

**Step 2: Add new elements**

Replace that entire block with the following (keep everything the same, just add the new elements):

```js
  // Floating buttons row
  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:6px;align-items:center;justify-content:flex-end;";

  const btn = document.createElement("button");
  btn.id = "eale-btn";
  btn.innerHTML = `<span class="dot"></span> EALE Check`;

  const learnBtn = document.createElement("button");
  learnBtn.id = "eale-learn-floating";
  learnBtn.innerHTML = `📚`;
  learnBtn.title = "Learn this topic";
  learnBtn.style.cssText = `
    background:#059669;color:#fff;border:none;border-radius:24px;
    padding:10px 13px;font-size:14px;cursor:pointer;
    box-shadow:0 4px 14px rgba(5,150,105,.4);
    transition:background .15s,transform .1s;
  `;
  learnBtn.onmouseenter = () => { learnBtn.style.background = "#047857"; learnBtn.style.transform = "translateY(-1px)"; };
  learnBtn.onmouseleave = () => { learnBtn.style.background = "#059669"; learnBtn.style.transform = ""; };

  // Camera toggle button (hidden until attentionMonitoring feature gate is on)
  const cameraBtn = document.createElement("button");
  cameraBtn.id = "eale-camera-btn";
  cameraBtn.innerHTML = `<span class="cam-indicator"></span> 📷`;
  cameraBtn.title = "Enable attention monitoring";
  cameraBtn.style.display = "none"; // hidden until feature gate loads

  // Stop Camera button (visible only when camera is active)
  const stopCameraBtn = document.createElement("button");
  stopCameraBtn.id = "eale-stop-camera-btn";
  stopCameraBtn.innerHTML = `⏹ Stop Camera`;
  stopCameraBtn.title = "Stop camera";

  btnRow.appendChild(stopCameraBtn);
  btnRow.appendChild(cameraBtn);
  btnRow.appendChild(learnBtn);
  btnRow.appendChild(btn);
  container.appendChild(btnRow);

  // Toast nudge (above button row)
  const camToast = document.createElement("div");
  camToast.id = "eale-cam-toast";
  camToast.innerHTML = `
    <span class="toast-text">📷 Turn on camera for attention tracking</span>
    <button class="toast-cam-on-btn">Camera On</button>
    <button class="toast-dismiss-btn" title="Dismiss">✕</button>
  `;
  container.insertBefore(camToast, btnRow);

  // Panel
  const panel = document.createElement("div");
  panel.id = "eale-panel";
  container.insertBefore(panel, camToast);
```

**Step 3: Manually verify**

Reload extension, open an allowed page. The button row should still show EALE Check + 📚. Camera button is hidden (no `attentionMonitoring` set yet). No console errors.

**Step 4: Commit**

```bash
git add chrome-extension/content.js
git commit -m "feat: add camera toggle, stop button, and toast DOM elements"
```

---

### Task 3: Update startAttentionMonitoring / stopAttentionMonitoring to sync button state

**Files:**
- Modify: `chrome-extension/content.js` — functions at ~line 743 and ~line 828

**Step 1: Add runtime camera state variable**

At the top of the IIFE, find the attention monitoring state block (~line 32):
```js
  // ── Attention monitoring state ─────────────────────────────────────────────
  let _attentionStream = null, _attentionVideo = null;
  let _attentionTimer = null, _faceAbsentSince = null;
```

Add one line after it:
```js
  let _cameraEnabled = false; // in-session camera state (independent of storage flag)
```

**Step 2: Update startAttentionMonitoring**

Find `startAttentionMonitoring` (~line 743). Right after `if (_attentionStream) return;` add the `_cameraEnabled` flag and button updates. Replace the function opening lines:

```js
  async function startAttentionMonitoring() {
    if (_attentionStream) return; // already running
    try {
      _attentionStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
    } catch (e) {
      console.warn("[EALE] Webcam access denied:", e);
      return;
    }

    _cameraEnabled = true;
    cameraBtn.classList.add("cam-on");
    cameraBtn.innerHTML = `<span class="cam-indicator"></span> 🎥`;
    cameraBtn.title = "Camera is active";
    stopCameraBtn.classList.add("visible");
    dismissCamToast(); // hide toast if showing
```

Everything after `_attentionStream = await ...` stays the same; just insert those 6 lines before the "Hidden video element" comment.

**Step 3: Update stopAttentionMonitoring**

Find `stopAttentionMonitoring` (~line 828). At the end of the function body, after `btn.classList.remove("attention-absent");`, add:

```js
    _cameraEnabled = false;
    cameraBtn.classList.remove("cam-on");
    cameraBtn.innerHTML = `<span class="cam-indicator"></span> 📷`;
    cameraBtn.title = "Enable attention monitoring";
    stopCameraBtn.classList.remove("visible");
```

**Step 4: Wire up cameraBtn and stopCameraBtn click handlers**

After the toast element is created (end of Task 2 block), add:

```js
  cameraBtn.addEventListener("click", () => {
    if (_cameraEnabled) {
      stopAttentionMonitoring();
    } else {
      startAttentionMonitoring();
    }
  });

  stopCameraBtn.addEventListener("click", () => {
    stopAttentionMonitoring();
  });
```

**Step 5: Manually verify**

1. Enable "Attention Monitoring" in extension Options, save.
2. Reload extension + reload an allowed page.
3. Camera button should now be visible (📷, grey pill).
4. Click it → browser asks for camera permission → click Allow → button turns green (🎥), "Stop Camera" appears.
5. Click "Stop Camera" → camera stops, button reverts to 📷, "Stop Camera" disappears.

**Step 6: Commit**

```bash
git add chrome-extension/content.js
git commit -m "feat: wire camera toggle button state to start/stop attention monitoring"
```

---

### Task 4: Remove auto-start; gate cameraBtn visibility on feature flag

**Files:**
- Modify: `chrome-extension/content.js` — settings load block (~line 1403-1419) and storage onChanged block (~line 1421-1438)

**Step 1: Update the initial settings load**

Find this block (~line 1403-1419):
```js
  chrome.storage.sync.get(
    ["backendUrl", "studentApiKey", "studentId", "allowlist", "useLlmContext", "useLlmGrading", "attentionMonitoring", "videoQuizEnabled"],
    (data) => {
      settings = { ... };
      if (settings.attentionMonitoring) startAttentionMonitoring();  // <-- REMOVE THIS LINE
      if (settings.videoQuizEnabled)    startVideoMonitoring();
    }
  );
```

Replace `if (settings.attentionMonitoring) startAttentionMonitoring();` with:
```js
      // Show camera button if feature is enabled in options; camera stays OFF until user clicks
      cameraBtn.style.display = settings.attentionMonitoring ? "" : "none";
```

**Step 2: Update the onChanged handler**

Find (~line 1429-1433):
```js
    if (changes.attentionMonitoring) {
      settings.attentionMonitoring = changes.attentionMonitoring.newValue;
      if (settings.attentionMonitoring) startAttentionMonitoring();
      else stopAttentionMonitoring();
    }
```

Replace with:
```js
    if (changes.attentionMonitoring) {
      settings.attentionMonitoring = changes.attentionMonitoring.newValue;
      cameraBtn.style.display = settings.attentionMonitoring ? "" : "none";
      if (!settings.attentionMonitoring && _cameraEnabled) {
        stopAttentionMonitoring(); // turn off camera if feature is disabled mid-session
      }
    }
```

**Step 3: Manually verify**

1. Options page → Attention Monitoring OFF → reload page → camera button is hidden.
2. Options page → Attention Monitoring ON → reload page → camera button visible (📷), camera NOT auto-started (no browser camera indicator in OS menu bar).
3. Click camera button → camera starts. Toggle feature off in options → camera stops automatically.

**Step 4: Commit**

```bash
git add chrome-extension/content.js
git commit -m "feat: camera no longer auto-starts; button visibility gated by feature flag"
```

---

### Task 5: Add 60-second toast nudge while video is playing and camera is off

**Files:**
- Modify: `chrome-extension/content.js` — attention monitoring state section + after the `stopAttentionMonitoring` function

**Step 1: Add nudge timer state variable**

In the attention monitoring state block (~line 32-36), add:
```js
  let _camNudgeTimer = null; // 60s interval — prompts user to enable camera during video
```

**Step 2: Add toast helper functions**

After the `stopAttentionMonitoring` function (~line 834), add:

```js
  // ── Camera nudge toast helpers ─────────────────────────────────────────────

  let _camToastDismissTimer = null;

  function showCamToast() {
    if (_cameraEnabled) return;           // camera already on
    if (!settings.attentionMonitoring) return; // feature not enabled
    const vid = detectVideo();
    if (!vid || vid.paused || vid.ended) return; // no video playing
    camToast.classList.add("visible");
    // Auto-dismiss after 8s
    clearTimeout(_camToastDismissTimer);
    _camToastDismissTimer = setTimeout(dismissCamToast, 8000);
  }

  function dismissCamToast() {
    camToast.classList.remove("visible");
    clearTimeout(_camToastDismissTimer);
    _camToastDismissTimer = null;
  }

  function startCamNudge() {
    if (_camNudgeTimer) return;
    _camNudgeTimer = setInterval(showCamToast, 60000);
  }

  function stopCamNudge() {
    if (_camNudgeTimer) { clearInterval(_camNudgeTimer); _camNudgeTimer = null; }
    dismissCamToast();
  }
```

**Step 3: Wire toast buttons**

Find the camera button click handler added in Task 3 and add toast wire-up right after it:

```js
  // Toast buttons
  camToast.querySelector(".toast-cam-on-btn").addEventListener("click", () => {
    dismissCamToast();
    startAttentionMonitoring();
  });
  camToast.querySelector(".toast-dismiss-btn").addEventListener("click", () => {
    dismissCamToast();
  });
```

**Step 4: Start/stop nudge alongside video monitoring**

Find `startVideoMonitoring()` (~line 841). At the very start of that function, after the guard `if (_videoHandlers) return;`, add:
```js
    startCamNudge();
```

Find `stopVideoMonitoring()` (search for it — it stops `_videoHandlers`). At the end of that function, add:
```js
    stopCamNudge();
```

Also in `startAttentionMonitoring`, after `dismissCamToast()` call, add:
```js
    stopCamNudge(); // camera is now on — stop nudging
```

And in `stopAttentionMonitoring` at the end (camera was stopped, restart nudge if video is playing):
```js
    if (settings.videoQuizEnabled) startCamNudge();
```

**Step 5: Manually verify**

1. Enable both "Attention Monitoring" and "Video Quiz Mode" in Options.
2. Open YouTube, play a video, do NOT click camera button.
3. Wait 60 seconds → toast appears: "📷 Turn on camera for attention tracking" with "Camera On" and ✕ buttons.
4. Click ✕ → toast disappears, reappears after another 60s.
5. Click "Camera On" → camera starts, toast disappears, nudge stops.
6. Stop camera → after next 60s cycle, toast reappears.

**Step 6: Commit**

```bash
git add chrome-extension/content.js
git commit -m "feat: add 60s camera nudge toast when video plays and camera is off"
```

---

### Task 6: Update options.html label and description

**Files:**
- Modify: `chrome-extension/options.html:297-306`

**Step 1: Find the Attention Monitoring toggle row**

Find (~line 297-306):
```html
      <div class="toggle-row">
        <div>
          <div class="toggle-label">Attention Monitoring</div>
          <div class="toggle-desc">Webcam detects when you look away; quizzes on return (needs CompVis on port 8001)</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" id="attentionMonitoring" />
          <span class="toggle-slider"></span>
        </label>
      </div>
```

**Step 2: Update the label and description**

Replace it with:
```html
      <div class="toggle-row">
        <div>
          <div class="toggle-label">Camera Button in Extension Bar</div>
          <div class="toggle-desc">Shows a camera toggle in the extension bar. Camera only activates when you click it — never auto-starts. Needs CompVis on port 8001.</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" id="attentionMonitoring" />
          <span class="toggle-slider"></span>
        </label>
      </div>
```

**Step 3: Manually verify**

Open extension options page. The Computer Vision section now reads "Camera Button in Extension Bar" with the updated description.

**Step 4: Commit**

```bash
git add chrome-extension/options.html
git commit -m "docs: update attention monitoring option label to reflect camera privacy model"
```

---

## Final Manual Test Checklist

After all tasks are complete, run through this full scenario:

1. Options → Attention Monitoring OFF → reload allowed page → camera button is **hidden**
2. Options → Attention Monitoring ON → reload allowed page → camera button is **visible** (📷 grey), camera is **not** auto-started (no OS camera indicator)
3. Click 📷 → browser permission prompt appears → Allow → button turns green (🎥) + green pulse dot + "Stop Camera" red button appears
4. Click "Stop Camera" → camera off → 📷 grey, no Stop Camera button
5. On YouTube with a video playing, camera off, wait 60s → toast appears
6. Click "Camera On" in toast → camera activates, toast gone, no more nudges
7. Options → Attention Monitoring OFF mid-session (while camera on) → camera stops automatically
8. Check OS menubar camera indicator matches extension camera state at all times
