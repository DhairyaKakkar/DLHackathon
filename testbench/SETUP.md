# EALE — Step-by-Step Setup & Testing Guide

Complete walkthrough for judges to set up and test every feature from scratch.

---

## Prerequisites

- **Docker + Docker Compose** (Docker Desktop 4.x or newer)
- **Chrome browser**
- **Python 3.x** (to generate extension icons — one command)
- **Your own OpenAI API key** — required for LLM features (question generation, grading, video lessons, roadmaps). All features have deterministic fallbacks without a key.

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/DhairyaKakkar/DLHackathon.git
cd DLHackathon
```

---

## Step 2 — Add Your OpenAI API Key

Open `docker-compose.yml` and paste your key on line 34:

```yaml
OPENAI_API_KEY: "sk-..."   # ← your own key here
```

> **Never commit your key.** The file has `OPENAI_API_KEY: ""` in git — fill it locally only.

---

## Step 3 — Start All Services

```bash
# First time (builds Docker images — takes 2-4 min):
docker compose up --build -d

# Subsequent starts (no code changes):
docker compose up -d

# Watch backend logs:
docker compose logs -f backend
```

Wait until you see:
```
backend-1  | INFO:     Application startup complete.
```

Verify everything is running:

```bash
curl http://localhost:8000/health   # → {"status": "ok"}
curl http://localhost:8001/health   # → {"status": "ok"}
```

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| CompVis (YOLOv8) | http://localhost:8001 |

---

## Step 4 — Install the Chrome Extension

```bash
cd chrome-extension
python3 generate_icons.py
# Generates: icons/icon16.png, icons/icon48.png, icons/icon128.png
cd ..
```

1. Open Chrome → `chrome://extensions`
2. Toggle **Developer mode** (top-right corner)
3. Click **Load unpacked** → navigate to `chrome-extension/` → select it
4. The **EALE** icon appears in the Chrome toolbar

**Configure the extension:**
1. Click the EALE icon → click **⚙ Options** (or right-click → Options)
2. Set **Backend URL**: `http://localhost:8000`
3. Set **Student API Key**: `student-alice-key`
4. Enable **LLM Question Generation** and **LLM Grading** (if you added an API key)
5. Click **Save**

---

## Step 5 — Enable YOLOv8 Attention Monitoring

Run once after `docker compose up`:

```bash
curl -X POST http://localhost:8001/switch-model \
  -H "Content-Type: application/json" \
  -d '{"model_name": "yolov8n", "config_overrides": {"task": "detection"}}'
```

Expected: `{"model": "yolov8n", "task": "detection", ...}`

---

## Step 6 — Verify Seed Data

```bash
curl -s http://localhost:8000/api/v1/students/ | python3 -m json.tool
# Expected: Alice Chen (id=1), Bob Martinez (id=2), Dana Faculty (id=3)

curl -s http://localhost:8000/api/v1/topics/ | python3 -m json.tool
# Expected: Python Basics (id=1), Data Structures (id=2), Algorithms (id=3)
```

---

## Step 7 — Sign In and Explore Dashboards

Go to **http://localhost:3000** — you'll see the EALE landing page.

Click **Sign In to Dashboard** and use one of these demo accounts:

| User | API Key | Role | What to look for |
|------|---------|------|-----------------|
| Alice Chen | `student-alice-key` | Student | High mastery (~80), low transfer (~15) — surface memorisation pattern |
| Bob Martinez | `student-bob-key` | Student | Overconfidence gap >30pp on Algorithms, DUS <25 |
| Dana Faculty | `faculty-dana-key` | Faculty | Cohort risk cards, DUS histogram, all student links |

### Student Dashboard (Alice — `student-alice-key`)

1. Sign in → redirected to Alice's dashboard
2. **Overview tab**: DUS hero card, 4 metric cards, per-topic breakdown table
3. **Roadmap tab**: Topics grouped by DUS tier
   - 🔴 Focus Now (DUS < 60) · 🟡 Reinforce (60-79) · 🟢 Mastered (≥ 80)
   - Click any topic card → GPT-4o generates a personalized roadmap modal with:
     - Diagnosis, key concepts, step-by-step study plan, curated links, estimated weeks to DUS 80
4. Click **Tasks** (top-right) → see spaced-repetition retests due

### Faculty Dashboard (Dana — `faculty-dana-key`)

Sign out → sign in with `faculty-dana-key`

What to see:
- **Risk cards**: Transfer Failures, Overconfidence Hotspots, AI Dependency Risk
- **Topic table**: per-topic avg metrics with `ai-risk`, `retention`, `transfer`, `overconf` flag badges
- **DUS histogram**: distribution of student×topic DUS scores
- **View individual students**: links to each student's dashboard

---

## Step 8 — Chrome Extension: Basic Quiz

1. Open `testbench/fake-lms.html` in Chrome (File → Open File, or drag into Chrome)
2. The page has Algorithms content (Big-O, binary search, sorting)
3. Click the **EALE Check** button (bottom-right)
4. Answer the question, set confidence, click **Submit Answer**
5. See result with correct answer, explanation, and updated DUS

---

## Step 9 — Chrome Extension: LLM Mode

With `USE_LLM_CONTEXT=true` and an API key:

1. Open any Wikipedia page or technical article
2. Click **EALE Check**
3. Loading reads "Generating question with AI…"
4. Question is contextually relevant to that specific page
5. Panel header shows **AI Generated** badge

---

## Step 10 — Video Quiz (YouTube)

1. Open any YouTube video (lecture, CS topic, etc.)
2. Try these triggers:

| Trigger | How to test | Expected |
|---------|-------------|----------|
| **Rewind** | Drag video scrubber backward >5s | Panel pops up with ⏪ badge |
| **Manual pause** | Press spacebar / click pause | Panel pops up with ⏸ badge |
| **Dense concept** | Let video play 3+ min (API key needed) | GPT-4o assesses frame; quiz if score ≥ 4/5 |

After answering → **Done** → video resumes automatically.

---

## Step 11 — Learn It (Sora AI Video Lesson)

1. Open any page or YouTube video
2. Click **📚** in the EALE overlay
3. Loading: "Generating animated video lesson…" (~15-90s)
4. A Sora-generated MP4 plays with TTS narration (or GPT-4o canvas animation as fallback)
5. Click **🔊 Narration** to toggle audio
6. Click **Quiz me →** → 2 GPT-4o quiz questions about the lesson

---

## Step 12 — Attention Monitoring (requires webcam)

1. Enable **Attention Monitoring** in extension Options + allow webcam access
2. Play a YouTube video
3. Look away for 25+ seconds → EALE button turns red
4. Look back → quiz triggers with 👀 "Welcome Back" badge

---

## Step 13 — Anti-Cheating Features

### Paste Detection + "Prove It"

Requires `USE_LLM_GRADING=true` and an API key.

1. Trigger any short-text question
2. **Copy-paste** an answer into the input box (Ctrl+V / Cmd+V)
3. Submit
4. Orange **🔍 Prove It** box appears with a GPT-4o follow-up question
5. The follow-up is impossible to answer without understanding the concept

### AI-Dependency Score

Faculty dashboard → **AI Dependency Risk** card shows flagged student names.
Topic table → **ai-risk** badge appears on topics matching the AI-dependency fingerprint:
- High mastery + low retention (forgets quickly)
- High mastery + low transfer (can't apply to new context)

---

## Step 14 — Handwritten Answer (requires API key)

1. Trigger a short-text question via the extension
2. Click **📷 Upload handwritten answer**
3. Upload a photo of a handwritten answer
4. Submit → GPT-4o OCRs and grades with feedback

---

## Step 15 — API (curl examples)

```bash
# Alice full dashboard
curl -s http://localhost:8000/api/v1/metrics/student/1 | python3 -m json.tool

# Bob + Algorithms only
curl -s http://localhost:8000/api/v1/metrics/student/2/topic/3 | python3 -m json.tool

# GPT-4o roadmap for Alice, Python Basics
curl -s http://localhost:8000/api/v1/metrics/student/1/topic/1/roadmap | python3 -m json.tool

# Faculty cohort view
curl -s http://localhost:8000/api/v1/metrics/faculty | python3 -m json.tool

# Due tasks for Alice
curl -s http://localhost:8000/api/v1/tasks/student/1 | python3 -m json.tool

# Submit an attempt
curl -s -X POST http://localhost:8000/api/v1/attempts/ \
  -H "Content-Type: application/json" \
  -d '{"student_id": 2, "question_id": 7, "answer": "O(log n)", "confidence": 9}' \
  | python3 -m json.tool

# Reset demo data
curl -s -X POST http://localhost:8000/api/v1/admin/reset
```

---

## Step 16 — Run Unit Tests

```bash
cd backend
PYTHONPATH=. python3.11 -m pytest tests/ -v
# Expected: 22 passed in < 1s (in-memory SQLite, no API key needed)
```

---

## Demo API Keys Reference

| User | API Key | Role |
|------|---------|------|
| Alice Chen | `student-alice-key` | student |
| Bob Martinez | `student-bob-key` | student |
| Dana Faculty | `faculty-dana-key` | faculty |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Backend not starting | `docker compose logs backend` |
| Extension not showing | Confirm loaded at `chrome://extensions` and enabled |
| Quiz panel not appearing | Check Options — backend URL and API key correct |
| LLM not generating | Check `OPENAI_API_KEY` in `docker-compose.yml` + `USE_LLM_CONTEXT=true` + run `docker compose up -d backend` (not restart) |
| Roadmap modal fails | Same as above — needs valid API key |
| CompVis webcam error | Webcam access must be allowed in Chrome; CompVis service must be running |
| Reset demo data | `curl -X POST http://localhost:8000/api/v1/admin/reset` |
| Frontend slow to load | First start compiles Next.js — wait 30-60s, then refresh |
