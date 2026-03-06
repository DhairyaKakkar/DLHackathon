# Camera Privacy Toggle — Design Doc
Date: 2026-03-07

## Problem
Camera (attention monitoring) auto-starts on page load if enabled in options — no in-session control, no visible indicator, no user awareness that the camera is active.

## Solution
Treat camera like a microphone: user always knows it's on, always controls it.
> "We treat attention monitoring like a microphone — you always know it's on, you always control it."

## Scope
Changes are confined to `chrome-extension/content.js` and `chrome-extension/options.html` / `options.js`.

---

## Design

### 1. Options Toggle — Feature Gate Only
- `attentionMonitoring` in `chrome.storage.sync` becomes a **feature gate** (shows/hides the camera button in the bar)
- Camera no longer auto-starts on page load even if `attentionMonitoring = true`
- Options page label updated to: "Enable Camera Button in Extension Bar"

### 2. Camera Toggle Button in Extension Bar
New `cameraBtn` added to `btnRow` (leftmost position):
- **Off state**: grey pill, icon `📷`, tooltip "Enable attention monitoring"
- **On state**: green pill, icon `🎥`, pulsing green dot (macOS-style indicator)
- Clicking toggles `startAttentionMonitoring()` / `stopAttentionMonitoring()`
- Hidden if `attentionMonitoring` feature gate is off

### 3. Persistent "Stop Camera" Button
- A red `Stop Camera` mini-button renders in `btnRow` when camera is active
- Always visible outside the EALE panel
- Calls `stopAttentionMonitoring()` + removes itself

### 4. Green Indicator Light
- 8×8px `border-radius:50%` green dot with `pulse-green` CSS animation
- Renders inline next to `cameraBtn` when camera is on
- Disappears immediately on camera stop

### 5. 60-Second Video Toast Nudge
**Trigger condition** (checked every 60s via `setInterval`):
- `attentionMonitoring` feature gate is enabled AND
- Camera is currently OFF AND
- A `<video>` element is detected playing on the page

**Toast UI** (shadow DOM, above `btnRow`):
- Slim horizontal card: "📷 Turn on camera for attention tracking"
- **"Camera On"** indigo button → calls `startAttentionMonitoring()` + dismisses toast
- **✕** dismiss button → dismisses toast, resets 60s timer
- Auto-dismisses after 8 seconds
- Does not stack — only one toast at a time

**Cleanup**: nudge interval cleared when camera turns on or page unloads.

---

## State Changes

| Before | After |
|--------|-------|
| Camera auto-starts on load if `attentionMonitoring=true` | Camera always starts OFF |
| Only options page controls camera | Bar toggle + "Stop Camera" button control camera |
| No visible active indicator | Green dot + green button when active |
| No nudge | 60s toast nudge while video playing + camera off |

---

## Files Changed
- `chrome-extension/content.js` — add `cameraBtn`, `stopCameraBtn`, indicator dot, toast nudge logic, update `startAttentionMonitoring` call site
- `chrome-extension/options.html` — update Attention Monitoring label/description
