# EALE — Grader Setup & Testing Guide

This document walks you through setting up EALE from scratch and verifying every feature end-to-end. All steps are self-contained.

---

## Prerequisites

- **Docker + Docker Compose** (tested on Docker Desktop 4.x)
- **Chrome browser** (for the extension)
- **Python 3.x** (only needed to generate extension icons — one command)
- **OpenAI API key** (optional — all features have deterministic fallbacks)

---

## Step 1 — Start All Services

```bash
git clone https://github.com/DhairyaKakkar/DLHackathon.git
cd DLHackathon
```

**Without LLM features (no API key needed):**
```bash
docker compose up --build
```

**With LLM + vision features:**
```bash
# Edit docker-compose.yml → backend → environment, set:
#   OPENAI_API_KEY=sk-...
#   USE_LLM_CONTEXT=true
#   USE_LLM_GRADING=true
docker compose up --build
```

Wait until you see:
```
backend-1  | INFO:     Application startup complete.
```

Verify all services are up:

```bash
curl http://localhost:8000/health
# → {"status": "ok"}

curl http://localhost:8001/health
# → {"status": "ok"}   (CompVis/YOLOv8 service)
```

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| CompVis (YOLOv8) | http://localhost:8001 |

---

## Step 2 — Install the Chrome Extension

```bash
cd chrome-extension
python3 generate_icons.py
# Generates icons/icon16.png, icon48.png, icon128.png
cd ..
```

1. Open Chrome → go to `chrome://extensions`
2. Toggle **Developer mode** (top-right corner)
3. Click **Load unpacked** → navigate to the `chrome-extension/` folder → select it
4. The **EALE** extension icon appears in the toolbar

**Configure the extension:**
1. Right-click the EALE icon → **Options**
2. Set **Backend URL**: `http://localhost:8000`
3. Set **Student API Key**: `student-alice-key`
4. Set **Student ID**: `1`
5. Enable **LLM Question Generation** and **LLM Grading** if you set an API key
6. Click **Save**

---

## Step 3 — Verify Seed Data

The system auto-seeds demo data on first boot. Confirm it's there:

```bash
curl -s http://localhost:8000/api/v1/students/ | python3 -m json.tool
```

Expected: Alice Chen (id=1), Bob Martinez (id=2), Dana Faculty (id=3)

```bash
curl -s http://localhost:8000/api/v1/topics/ | python3 -m json.tool
```

Expected: Python Basics (id=1), Data Structures (id=2), Algorithms (id=3)

---

## Step 4 — Frontend Dashboards

### Student Dashboard — Alice (Fragile Mastery)

Open: **http://localhost:3000/student/1**

What to see:
- **Mastery** ≈ 80+ on Python Basics — she gets original questions right
- **Transfer** ≈ 10–30 — she fails rephrased/variant questions (surface memorisation pattern)
- **DUS** significantly lower than mastery — the gap reveals fragile learning
- Retention curve with a drop after 3+ days

### Student Dashboard — Bob (Overconfident)

Open: **http://localhost:3000/student/2**

What to see:
- **Overconfidence gap** > 30pp on Algorithms (confidence 8–9/10, accuracy < 25%)
- **Calibration** < 30 on Data Structures
- **DUS** < 25 on Algorithms

### Faculty Dashboard

Open: **http://localhost:3000/faculty**

What to see:
- Risk cards: Transfer Failures, Overconfidence Hotspots, AI Dependency Risk
- Topic table with `ai-risk`, `retention`, `transfer`, `overconf` flag badges
- DUS distribution histogram

---

## Step 5 — Backend API (curl)

### Student metrics

```bash
# Alice full dashboard
curl -s http://localhost:8000/api/v1/metrics/student/1 | python3 -m json.tool

# Bob + Algorithms only
curl -s http://localhost:8000/api/v1/metrics/student/2/topic/3 | python3 -m json.tool

# Faculty cohort view
curl -s http://localhost:8000/api/v1/metrics/faculty | python3 -m json.tool
```

### Due tasks (spaced repetition queue)

```bash
curl -s http://localhost:8000/api/v1/tasks/student/1 | python3 -m json.tool
```

### Submit an attempt manually

```bash
curl -s -X POST http://localhost:8000/api/v1/attempts/ \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": 2,
    "question_id": 7,
    "answer": "O(log n)",
    "confidence": 9,
    "reasoning": "Binary search halves the search space"
  }' | python3 -m json.tool
```

After this, a RETEST task is auto-scheduled. Check it:
```bash
curl -s "http://localhost:8000/api/v1/tasks/student/2?include_future=true" | python3 -m json.tool
```

### Reset to clean demo state

```bash
curl -s -X POST http://localhost:8000/api/v1/admin/reset | python3 -m json.tool
```

---

## Step 6 — Chrome Extension: Basic Quiz

1. Open `testbench/fake-lms.html` in Chrome (File → Open File, or drag into Chrome)
2. The page contains Algorithms content (Big-O, binary search, sorting)
3. Click the **EALE Check** button (bottom-right of the page)
4. A quiz panel slides up with a relevant question
5. Select/type an answer, set confidence, click **Submit Answer**
6. See the result with correct answer and updated DUS

**What to verify:**
- Question is about Algorithms (keyword match)
- Result shows correct/incorrect + explanation
- Updated DUS appears at the bottom of the result

---

## Step 7 — Chrome Extension: LLM Mode (requires API key)

Enable LLM in extension Options → LLM Question Generation ON.

1. Open any article or Wikipedia page on a technical topic
2. Click **EALE Check**
3. Loading message reads "Generating question with AI…"
4. Question is contextually relevant to that specific page
5. Badge in the panel header shows **AI Generated**

With a screenshot: the extension captures the visible tab and sends it alongside the page text — GPT-4o can read diagrams, equations, and code blocks.

---

## Step 8 — Video Quiz (YouTube / Khan Academy)

1. Open any YouTube video (e.g., a lecture on algorithms or CS topic)
2. Make sure **Video Quiz Mode** is enabled in extension Options
3. Try these triggers:

| Trigger | How to test | Expected |
|---------|-------------|----------|
| **Rewind** | Drag the video scrubber backward >5s | Panel pops up immediately with ⏪ badge |
| **Manual pause** | Press spacebar or click pause | Panel pops up with ⏸ badge |
| **Dense concept** | Let video play for 3+ min (if API key set) | GPT-4o silently assesses; quiz if score ≥ 4/5 |

After answering, click **Done** — video resumes automatically.

**Note:** Typing in the quiz panel does NOT trigger YouTube shortcuts (shadow DOM isolation).

---

## Step 9 — Attention Monitoring (requires webcam)

1. Enable **Attention Monitoring** in extension Options
2. Allow webcam access when prompted
3. Look away from the screen for 25+ seconds while a video is playing
4. The EALE button turns red and pulses
5. Look back at the screen → quiz triggers with 👀 "Welcome Back" badge

For reading/note-taking (no video playing): look away for 60+ seconds → quiz triggers directly.

---

## Step 10 — Handwritten Answer (requires API key with USE_LLM_GRADING=true)

1. Trigger a quiz that shows a short-text (open-ended) question
2. Below the text input, click **📷 Upload handwritten answer**
3. Take a photo of a handwritten answer and upload it
4. Submit — GPT-4o OCRs the image and grades it with feedback

---

## Step 11 — Anti-Cheating Features

### Paste Detection + "Prove It"

Requires: `USE_LLM_GRADING=true` and a valid OpenAI API key.

1. Trigger any short-text question via the extension
2. Find the correct answer (from API docs, seed data, or a quick search)
3. **Copy-paste** the answer into the text box (Ctrl+V / Cmd+V)
4. Submit the answer
5. In the result panel, an orange **🔍 Prove It** box appears with a follow-up question
6. The follow-up asks you to explain a concept from your answer — impossible to answer without understanding it

### AI-Dependency Score (faculty view)

The faculty dashboard at http://localhost:3000/faculty shows:
- **AI Dependency Risk** card — lists student names flagged
- Topic table **ai-risk** badge — topics where the cohort fingerprint matches AI-dependent patterns

The score is computed from: retention collapse (mastery >> retention), transfer gap (mastery >> transfer), and calibration paradox (well-calibrated at first, no recall later).

---

## Step 12 — Run Unit Tests

```bash
cd backend
PYTHONPATH=. python3.11 -m pytest tests/ -v
```

Expected output:
```
22 passed in < 1s
```

All 22 tests run against in-memory SQLite — no external dependencies, no API key needed.

---

## Seed API Keys Reference

| User | API Key | Role |
|------|---------|------|
| Alice Chen | `student-alice-key` | student |
| Bob Martinez | `student-bob-key` | student |
| Dana Faculty | `faculty-dana-key` | faculty |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Backend not starting | Check Docker logs: `docker compose logs backend` |
| Extension not showing | Confirm it's loaded at `chrome://extensions` and enabled |
| Quiz panel not appearing | Check extension Options — backend URL and API key |
| LLM not generating | Confirm `OPENAI_API_KEY` in `docker-compose.yml` and `USE_LLM_CONTEXT=true` |
| CompVis webcam error | Webcam access must be allowed in Chrome; CompVis service must be running |
| YouTube keyboard issue | Should not happen — shadow DOM blocks key events; reload extension if it does |
| Reset demo data | `curl -X POST http://localhost:8000/api/v1/admin/reset` |
