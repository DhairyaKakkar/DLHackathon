# EALE Chrome Extension

Attaches EALE micro-quizzes to any learning page. Click the floating **"EALE Check"** button to receive a knowledge check question matched to what you're studying, then see immediate feedback on correctness and calibration.

---

## Architecture

```
chrome-extension/
├── manifest.json       MV3 manifest
├── background.js       Service worker — storage defaults, auto-pop alarms
├── content.js          Shadow-DOM overlay widget (quiz state machine)
├── options.html/.js    Settings page — API URL, API key, allowlist, timer
├── popup.html/.js      Toolbar popup — student switch, trigger quiz
├── generate_icons.py   One-off script to generate PNG icons
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

### Two new backend endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/extension/context` | Pick the best question for the current page |
| `POST` | `/api/v1/extension/submit` | Record an attempt; return feedback + calibration note |

Both require the `X-API-Key` header (same key used by the EALE dashboard).

### Question selection priority

1. **Due task** — RETEST or TRANSFER task that is already past `due_at`
2. **Inferred topic** — keywords on the page matched against topic keyword map
3. **Random fallback** — unanswered question from any topic

---

## Install (Load Unpacked)

1. Make sure the EALE backend is running at `http://localhost:8000`
   ```bash
   docker compose up db backend -d
   ```

2. Generate icons (one time):
   ```bash
   cd chrome-extension
   python3 generate_icons.py
   ```

3. Open Chrome and navigate to `chrome://extensions/`

4. Enable **Developer mode** (toggle in top-right)

5. Click **Load unpacked** → select the `chrome-extension/` folder

6. The EALE extension icon appears in the toolbar

---

## Configuration

Click the extension icon → **⚙ Options** (or right-click the icon → "Options"):

| Setting | Default | Notes |
|---------|---------|-------|
| API URL | `http://localhost:8000` | Where the backend is running |
| API Key | `student-alice-key` | From seed data |
| Auto-pop | `0` (disabled) | Minutes between automatic quiz prompts |
| Allowlist | `localhost`, `*.canvas…` | URL patterns that activate the button |

**Demo API keys:**
- Alice Chen (fragile mastery): `student-alice-key`
- Bob Martinez (overconfident): `student-bob-key`

---

## Demo Flows

### Flow 1 — Fake LMS (keyword inference)

1. Open `testbench/fake-lms.html` in Chrome (file://... URL)
   - This page covers Algorithms topics: binary search, sorting, Big O, dynamic programming
2. Click the indigo **EALE Check** button in the bottom-right corner
3. The extension posts the page text to `/api/v1/extension/context`
4. Backend infers **Algorithms** topic from keyword matches and serves a question
5. Answer → confidence slider → Submit
6. See immediate feedback: correct/incorrect + calibration note

### Flow 2 — Due task (spaced repetition)

1. Select **Bob Martinez** in the popup (overconfident student with due tasks)
2. Navigate to any allowed page
3. Click **Trigger EALE Check on Current Tab** in the popup (or the page button)
4. Backend finds Bob's oldest overdue RETEST task and serves it
5. Notice the **RETEST** badge on the quiz panel

### Flow 3 — Options page

1. Click the extension icon → ⚙ Options
2. Change the API key to `student-bob-key`
3. Add a custom URL pattern to the allowlist (e.g. `coursera.org`)
4. Click **Save Settings**
5. Settings persist via `chrome.storage.sync`

---

## How the Overlay Works

The content script injects a **Shadow DOM** widget so its CSS is 100% isolated from the host page. No styles leak in or out.

Quiz state machine:
```
idle ──[click button]──► loading ──[fetch ok]──► quiz ──[submit]──► submitting ──► result
                                └──[fetch err]──► error
```

The floating button glows with an animated dot when the extension is active on an allowed page.
