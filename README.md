# EALE — Evidence-Aligned Learning Engine

> A Chrome Extension + backend system that embeds **durable-learning assessment** directly into the browser — quizzing students on content they're actively reading or watching, generating Sora AI video lessons, detecting AI-dependency, and giving faculty real-time cohort insights.

---

## The Problem

Modern students can answer questions correctly in the moment — by copying answers, using AI tools, or memorising surface patterns — while retaining nothing a week later. Standard LMS quizzes cannot distinguish **genuine understanding** from **surface compliance**.

EALE solves this with three layers:

1. **The DUS metric** — a formula that measures learning durability, not just accuracy
2. **The Chrome Extension** — embeds micro-quizzes in whatever the student is already doing (reading a paper, watching a lecture video)
3. **Anti-cheating signals** — paste detection, AI-dependency fingerprint, and "Prove It" follow-up questions

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Chrome Extension (MV3)                                         │
│  Shadow DOM overlay · GPT-4o page reader · video quiz engine    │
│  YOLOv8 attention monitor · paste detection · Prove It UI       │
│  Learn It: Sora AI video + TTS narration                        │
└──────────────┬──────────────────────────────┬───────────────────┘
               │ REST (X-API-Key)              │ REST (X-API-Key)
               ▼                              ▼
┌──────────────────────────┐    ┌───────────────────────────────┐
│  FastAPI Backend          │    │  CompVis Service (port 8001)  │
│  port 8000                │    │  YOLOv8n inference API        │
│  SQLAlchemy + PostgreSQL  │    │  person detection from webcam │
│  APScheduler (spaced rep) │    └───────────────────────────────┘
│  OpenAI GPT-4o + Sora     │
│  YouTube transcript API   │
└──────────────┬────────────┘
               │
               ▼
┌──────────────────────────┐
│  Next.js 14 Frontend     │
│  port 3000               │
│  Student + Faculty views │
└──────────────────────────┘
```

---

## The DUS Formula

```
DUS = 0.30 × mastery
    + 0.30 × retention
    + 0.25 × transfer_robustness
    + 0.15 × calibration
```

| Component | What it measures | How |
|-----------|-----------------|-----|
| **Mastery** | Recent accuracy on original questions | Last 10 attempts |
| **Retention** | Does accuracy hold over time? | Bins: same-day → week+; penalises drops |
| **Transfer** | Does knowledge generalise to rephrased questions? | Variant accuracy ÷ original accuracy |
| **Calibration** | Is confidence matched to accuracy? | ECE-like score across 5 confidence bins |

DUS ≥ 80 = Durable · 60–79 = Partial · < 60 = Fragile

---

## AI-Dependency Score

```
retention_collapse = max(0, mastery − retention) / 100
transfer_gap       = max(0, mastery − transfer)  / 100
calib_paradox      = 0.5  if (mastery ≥ 70 AND |overconf_gap| < 10 AND retention < 60)
                          else 0

AI_Dependency = (0.45 × retention_collapse + 0.45 × transfer_gap + 0.10 × calib_paradox) × 100
```

**Flagged** when score ≥ 40 and mastery ≥ 60 — high apparent performance with no evidence of real learning.

---

## Key Features

### Learn It — Sora AI Video Lessons
- Click **📚** in the extension overlay on any page or YouTube video
- Backend calls GPT-4o to write a cinematic Sora video prompt, then calls Sora (`sora` model, 1280×720, 8s) to generate an actual MP4 video
- OpenAI TTS-1-HD narration audio plays alongside the video in perfect sync
- If Sora is unavailable (account not yet enabled), falls back silently to a GPT-4o canvas animation
- Fullscreen button: native video fullscreen for Sora MP4; blob tab for HTML animation
- YouTube enrichment: if the current page is a YouTube video, the backend fetches the real transcript and uses it to make the lesson directly relevant to what's playing
- After watching: 2 GPT-4o quiz questions test understanding of the lesson

### Chrome Extension
- **GPT-4o page reader** — captures tab screenshot + visible text → generates a transfer-style question contextually relevant to what the student is studying
- **YouTube transcript enrichment** — fetches actual spoken captions for YouTube videos and uses them as context for question generation
- **Video quiz engine** — auto-pauses on rewind (>5s), manual pause, and dense-concept detection (GPT-4o assesses video frame every 3 min); resumes video after quiz
- **Attention monitoring** — YOLOv8 webcam feed via CompVis service; EALE button flashes red after 20s face absence during video; triggers quiz on attention return; triggers quiz after 60s absence while reading
- **Handwritten answer OCR** — photo upload for open-ended questions; GPT-4o reads and grades the handwriting in one vision call
- **Paste detection** — tracks paste events on the answer input; sends `answer_pasted: true` to backend
- **"Prove It" follow-up** — when paste detected, GPT-4o generates a contextual follow-up the student must explain to prove real comprehension
- **Shadow DOM isolation** — quiz overlay fully encapsulated; keyboard events blocked from leaking to YouTube/Khan Academy player
- **No repeat questions** — extension only shows LLM-generated or keyword-matched questions, never spaced-repetition retests (those live only in the student dashboard)

### Backend
- **Spaced repetition scheduler** — APScheduler creates RETEST tasks (24h) and TRANSFER tasks (72h) after each incorrect or low-confidence attempt
- **LLM question generation** — OpenAI generates questions from page context with TTL cache; per-student 60s rate limit (bypassed for video triggers)
- **LLM grading** — rubric-based grading for short-text answers; vision grading for handwritten uploads
- **Video difficulty assessment** — silent GPT-4o call every 3 min while video plays; only interrupts when score ≥ 4/5

### Faculty Dashboard
- Per-topic: avg mastery, retention, transfer, calibration, DUS, overconfidence gap
- Risk cards: Low Retention · Transfer Failures · Overconfidence Hotspots · **AI Dependency Risk**
- Per-student AI-dependency flag when cheating fingerprint detected
- DUS distribution histogram across cohort

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Chrome browser
- Python 3 (for icon generation script)
- OpenAI API key (required for LLM + Sora features; full deterministic fallback without it)

### Step 1 — Add your OpenAI API key

Open `docker-compose.yml` and set `OPENAI_API_KEY` under the `backend` service environment:

```yaml
environment:
  OPENAI_API_KEY: "sk-..."       # ← your key here
  OPENAI_MODEL: "gpt-4o"
  USE_LLM_CONTEXT: "true"
  USE_LLM_GRADING: "true"
```

> **Important:** Never commit the key. The file has `OPENAI_API_KEY: ""` in git — fill it locally only.

### Step 2 — Start all Docker services

```bash
# First time (or after requirements.txt changes):
docker compose up --build -d

# Subsequent starts (no code changes):
docker compose up -d

# Watch backend logs:
docker compose logs -f backend
```

Wait for: `INFO:     Application startup complete.`

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| CompVis (YOLOv8) | http://localhost:8001 |

### Step 3 — Install Chrome Extension

```bash
cd chrome-extension
python3 generate_icons.py   # generates icons/icon16.png, icon48.png, icon128.png
```

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → select the `chrome-extension/` folder
4. Click the **EALE** extension icon in the toolbar → **Options**
5. Set **Student API Key** to `student-alice-key`
6. Set **Backend URL** to `http://localhost:8000`
7. Save

> After any change to `content.js` or `manifest.json`, go to `chrome://extensions` and click the reload button on the EALE card.

### Step 4 — Enable YOLOv8 Attention Monitoring

The attention monitor needs the CompVis service running (it's part of `docker compose up`) and the correct model loaded:

```bash
# Switch CompVis to YOLOv8 detection mode (run once after docker compose up):
curl -X POST http://localhost:8001/switch-model \
  -H "Content-Type: application/json" \
  -d '{"model_name": "yolov8n", "config_overrides": {"task": "detection"}}'
```

Expected response: `{"model": "yolov8n", "task": "detection", ...}`

The EALE button in the extension will show a **camera icon** and turn **red** when no face is detected for 20s.

### Step 5 — View Dashboards

- Student (Alice — fragile mastery): http://localhost:3000/student/1
- Student (Bob — overconfident): http://localhost:3000/student/2
- Faculty cohort view: http://localhost:3000/faculty

### Step 6 — Test the Extension

**Basic quiz flow:**
Open `testbench/fake-lms.html` in Chrome — it contains Algorithms content that triggers keyword matching. Click the **EALE Check** button.

**Video quiz flow:**
Open any YouTube video and rewind more than 5 seconds — the extension auto-pauses and shows a GPT-4o question generated from the video's actual transcript.

**Learn It (Sora video lesson):**
Click the **📚** button in the overlay on any page. The backend generates a Sora video + TTS narration (~60–90s). After watching, click **Quiz me →**.

Full grader walkthrough: **`testbench/SETUP.md`**

---

## Stopping Services

```bash
docker compose down          # stop and remove containers
docker compose down -v       # also wipe the postgres data volume
```

---

## Restarting After Changes

```bash
# After editing backend Python files (hot-reload is on, so usually automatic):
# No action needed — uvicorn --reload picks up changes

# After editing docker-compose.yml environment variables:
docker compose up -d backend     # recreates the container with new env vars
# ⚠️  docker compose restart does NOT re-read env vars — always use up -d

# After editing requirements.txt (adding/upgrading packages):
docker compose up --build -d backend

# After editing chrome-extension/content.js or manifest.json:
# Go to chrome://extensions → click Reload on EALE
```

---

## Running Tests

```bash
cd backend
PYTHONPATH=. python3.11 -m pytest tests/ -v
# 22 tests, < 1 second, no external dependencies (in-memory SQLite)
```

---

## Resetting Demo Data

```bash
curl -X POST http://localhost:8000/api/v1/admin/reset
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://eale:eale_secret@db:5432/eale` | Postgres DSN |
| `OPENAI_API_KEY` | `` | OpenAI key — required for LLM + Sora features |
| `OPENAI_MODEL` | `gpt-4o` | Model for question gen, grading, video assessment |
| `USE_LLM_CONTEXT` | `false` | Enable LLM question generation + Learn It |
| `USE_LLM_GRADING` | `false` | Enable LLM grading + Prove It |
| `LLM_CACHE_TTL_SECONDS` | `600` | Question cache TTL (seconds) |
| `AUTO_SEED` | `true` | Seed demo data on startup |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `SCHEDULER_INTERVAL_SECONDS` | `60` | Spaced-rep scheduler interval |

---

## Demo Seed Data

Auto-seeded on first boot — no manual setup needed:

| User | API Key | Pattern |
|------|---------|---------|
| Alice Chen | `student-alice-key` | High mastery, low transfer (memorises surface form) |
| Bob Martinez | `student-bob-key` | Severely overconfident (high confidence, low accuracy) |
| Dana Faculty | `faculty-dana-key` | Faculty role |

3 Topics · 14 Questions (8 original + 6 variants) · 30+ Attempts with realistic timestamps demonstrating all metric patterns

---

## Project Structure

```
DLHackathon/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, lifespan, routers
│   │   ├── models.py                  # SQLAlchemy models
│   │   ├── schemas.py                 # Pydantic v2 schemas
│   │   ├── config.py                  # Pydantic-settings env config
│   │   ├── routers/
│   │   │   ├── extension.py           # Chrome extension endpoints
│   │   │   └── metrics.py             # Dashboard endpoints
│   │   └── services/
│   │       ├── metrics_service.py     # DUS + AI-dependency formula
│   │       ├── llm_service.py         # OpenAI: gen, grade, vision, Sora, TTS
│   │       ├── youtube_service.py     # YouTube transcript fetching
│   │       ├── scheduler_service.py   # Spaced repetition scheduler
│   │       └── seed.py                # Demo data
│   ├── requirements.txt
│   └── tests/
├── chrome-extension/
│   ├── manifest.json                  # MV3 manifest
│   ├── content.js                     # Shadow DOM overlay + all quiz + Learn It logic
│   ├── background.js                  # Screenshot capture, settings defaults
│   ├── options.html / options.js      # Extension settings page
│   └── popup.html / popup.js         # Extension popup
├── CompVis/                           # YOLOv8n inference service (Docker, port 8001)
├── frontend/
│   └── src/app/
│       ├── student/[id]/              # Student dashboard
│       └── faculty/                   # Faculty cohort dashboard
├── testbench/
│   ├── SETUP.md                       # Step-by-step grader guide
│   ├── fake-lms.html                  # Simulated LMS page for testing
│   ├── sample_curl.sh                 # API curl examples
│   └── test_llm_mode.sh               # LLM flow end-to-end test
└── docker-compose.yml
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy (sync), psycopg2, APScheduler |
| Database | PostgreSQL 15 |
| AI / Video | OpenAI GPT-4o (text + vision), Sora (video generation), TTS-1-HD (narration), YOLOv8n |
| Transcripts | youtube-transcript-api (no API key needed) |
| Frontend | Next.js 14 App Router, TypeScript, Tailwind CSS, TanStack Query, Recharts |
| Extension | Chrome MV3, Shadow DOM, chrome.storage.sync |
| Config | Pydantic v2 + pydantic-settings |
| Infra | Docker Compose (4 services: db, backend, compvis, frontend) |
