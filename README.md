# EALE — Evidence-Aligned Learning Engine

> A Chrome Extension + full-stack system that embeds **durable-learning assessment** directly into the browser — quizzing students contextually, generating AI video lessons, detecting AI-dependency, and giving faculty real-time cohort insights with personalised learning roadmaps.

---

## The Problem

Students can score well on quizzes by copying answers, using AI tools, or memorising surface patterns — while retaining nothing a week later. Standard LMS quizzes cannot distinguish **genuine understanding** from **surface compliance**.

EALE solves this with three layers:

1. **The DUS metric** — a formula that measures learning durability, not just accuracy
2. **The Chrome Extension** — embeds micro-quizzes in whatever the student is already doing
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
               │ REST (X-API-Key)              │ REST
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
│  Roadmap tab (GPT-4o)    │
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
- Backend calls GPT-4o to write a cinematic Sora video prompt, then calls Sora (`sora` model, 1280×720) to generate an MP4 video
- OpenAI TTS-1-HD narration audio plays alongside the video
- Falls back to a GPT-4o canvas animation if Sora is unavailable
- YouTube enrichment: backend fetches the real transcript and makes the lesson relevant to what's playing
- After watching: 2 GPT-4o quiz questions test understanding of the lesson

### Learning Roadmap (GPT-4o powered)
- Student dashboard has an **Overview** tab and a **Roadmap** tab
- Roadmap groups topics into 3 tiers: 🔴 Focus Now · 🟡 Reinforce · 🟢 Mastered (based on DUS)
- Clicking any topic card opens a GPT-4o generated modal with:
  - **Diagnosis** — why they're struggling (based on weak metric pattern)
  - **Key concepts** to focus on
  - **Step-by-step study plan** with time estimates
  - **Curated resources** with real links (YouTube, Wikipedia, LeetCode, Khan Academy, CS50, etc.)
  - **Estimated weeks** to reach DUS 80

### Chrome Extension
- **GPT-4o page reader** — captures tab screenshot + visible text → generates a transfer-style question contextually relevant to the student's current content
- **YouTube transcript enrichment** — fetches actual spoken captions for YouTube videos and uses them as question context
- **Video quiz engine** — auto-pauses on rewind (>5s), manual pause, and dense-concept detection (GPT-4o assesses video frame every 3 min)
- **Attention monitoring** — YOLOv8 webcam feed; EALE button flashes red after 20s face absence; triggers quiz on attention return
- **Handwritten answer OCR** — photo upload for open-ended questions; GPT-4o reads and grades in one vision call
- **Paste detection + "Prove It"** — detects copy-paste; GPT-4o generates a follow-up to verify real comprehension
- **Shadow DOM isolation** — quiz overlay fully encapsulated; no keyboard event leakage to YouTube/Khan Academy

### Dashboards
- **Student dashboard** — DUS hero, 4 metric cards, per-topic breakdown table, Roadmap tab
- **Faculty dashboard** — cohort aggregates, risk cards (Low Retention, Transfer Failures, Overconfidence, AI Dependency), DUS histogram, per-student links
- **Role-based auth** — students see only their own dashboard; faculty can view any student

---

## ⚠️ API Key Required

You must supply your own OpenAI API key to enable LLM features (question generation, grading, video lessons, roadmaps). The system works without a key but falls back to deterministic keyword-based questions.

Set it in `docker-compose.yml` before starting:

```yaml
OPENAI_API_KEY: "sk-..."   # ← paste your own key here, never commit it
```

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Chrome browser
- Python 3 (for extension icon generation — one command)
- OpenAI API key (your own — see above)

### Step 1 — Clone and add your API key

```bash
git clone https://github.com/DhairyaKakkar/DLHackathon.git
cd DLHackathon
```

Open `docker-compose.yml` and set your key under the `backend` service:

```yaml
environment:
  OPENAI_API_KEY: "sk-..."       # ← your key here
  OPENAI_MODEL: "gpt-4o"
  USE_LLM_CONTEXT: "true"
  USE_LLM_GRADING: "true"
```

### Step 2 — Start all Docker services

```bash
# First time (or after requirements.txt changes):
docker compose up --build -d

# Subsequent starts:
docker compose up -d

# Watch logs:
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
cd ..
```

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → select the `chrome-extension/` folder
4. Click the EALE icon → **Options**
5. Set **Student API Key** to `student-alice-key`
6. Set **Backend URL** to `http://localhost:8000`
7. Save

### Step 4 — Enable YOLOv8 Attention Monitoring

```bash
curl -X POST http://localhost:8001/switch-model \
  -H "Content-Type: application/json" \
  -d '{"model_name": "yolov8n", "config_overrides": {"task": "detection"}}'
```

### Step 5 — Sign in to the Dashboard

Go to **http://localhost:3000** and sign in with one of the demo accounts:

| User | API Key | Role | Pattern |
|------|---------|------|---------|
| Alice Chen | `student-alice-key` | Student | High mastery, low transfer (surface memorisation) |
| Bob Martinez | `student-bob-key` | Student | Severely overconfident (high confidence, low accuracy) |
| Dana Faculty | `faculty-dana-key` | Faculty | Cohort view + all student dashboards |

### Step 6 — Test the Extension

Open `testbench/fake-lms.html` in Chrome — it has Algorithms content that triggers keyword matching. Click the **EALE Check** button in the bottom-right corner.

Full step-by-step grader walkthrough: **`testbench/SETUP.md`**

---

## Stopping Services

```bash
docker compose down          # stop and remove containers
docker compose down -v       # also wipe the postgres data volume
```

---

## Restarting After Changes

```bash
# After editing docker-compose.yml environment variables:
docker compose up -d backend     # recreates container with new env vars
# ⚠️  docker compose restart does NOT re-read env vars — always use up -d

# After editing requirements.txt:
docker compose up --build -d backend

# After editing chrome-extension/content.js or manifest.json:
# chrome://extensions → click Reload on EALE
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
| `OPENAI_API_KEY` | `` | **Your own OpenAI key** — required for LLM + Sora features |
| `OPENAI_MODEL` | `gpt-4o` | Model for question gen, grading, roadmaps, video assessment |
| `USE_LLM_CONTEXT` | `false` | Enable LLM question generation + Learn It |
| `USE_LLM_GRADING` | `false` | Enable LLM grading + Prove It |
| `DATABASE_URL` | `postgresql://eale:eale_secret@db:5432/eale` | Postgres DSN |
| `LLM_CACHE_TTL_SECONDS` | `600` | Question cache TTL (seconds) |
| `AUTO_SEED` | `true` | Seed demo data on startup |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `SCHEDULER_INTERVAL_SECONDS` | `60` | Spaced-rep scheduler interval |

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
│   │   │   ├── metrics.py             # Dashboard + roadmap endpoints
│   │   │   └── auth.py                # API key validation
│   │   └── services/
│   │       ├── metrics_service.py     # DUS + AI-dependency formula
│   │       ├── llm_service.py         # OpenAI: gen, grade, vision, Sora, TTS, roadmap
│   │       ├── youtube_service.py     # YouTube transcript fetching
│   │       ├── scheduler_service.py   # Spaced repetition scheduler
│   │       └── seed.py                # Demo data
│   ├── requirements.txt
│   └── tests/                         # 22 unit tests (in-memory SQLite)
├── chrome-extension/
│   ├── manifest.json                  # MV3 manifest
│   ├── content.js                     # Shadow DOM overlay + quiz + Learn It logic
│   ├── background.js                  # Screenshot capture, settings defaults
│   ├── options.html / options.js      # Extension settings page
│   └── popup.html / popup.js         # Extension popup
├── CompVis/                           # YOLOv8n inference service (Docker, port 8001)
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── login/                 # Auth page (API key sign-in)
│       │   ├── student/[id]/          # Student dashboard (Overview + Roadmap tabs)
│       │   └── faculty/               # Faculty cohort dashboard
│       └── components/
│           ├── LearningPath.tsx       # Roadmap tier view
│           └── TopicRoadmapModal.tsx  # GPT-4o roadmap modal
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
| Transcripts | youtube-transcript-api (no extra API key needed) |
| Frontend | Next.js 14 App Router, TypeScript, Tailwind CSS, TanStack Query, Recharts |
| Extension | Chrome MV3, Shadow DOM, chrome.storage.sync |
| Config | Pydantic v2 + pydantic-settings |
| Infra | Docker Compose (4 services: db, backend, compvis, frontend) |
