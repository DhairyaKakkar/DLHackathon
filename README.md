# EALE — Evidence-Aligned Learning Engine

> A Chrome Extension + backend system that embeds **durable-learning assessment** directly into the browser — quizzing students on content they're actively reading or watching, detecting AI-dependency, and giving faculty real-time cohort insights.

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
└──────────────┬──────────────────────────────┬───────────────────┘
               │ REST (X-API-Key)              │ REST (X-API-Key)
               ▼                              ▼
┌──────────────────────────┐    ┌───────────────────────────────┐
│  FastAPI Backend          │    │  CompVis Service (port 8001)  │
│  port 8000                │    │  YOLOv8n inference API        │
│  SQLAlchemy + PostgreSQL  │    │  person detection from webcam │
│  APScheduler (spaced rep) │    └───────────────────────────────┘
│  OpenAI GPT-4o            │
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

A secondary metric computed from existing attempt data (no extra DB columns):

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

### Chrome Extension
- **GPT-4o page reader** — captures tab screenshot + visible text → generates a transfer-style question contextually relevant to what the student is studying
- **Video quiz engine** — auto-pauses on rewind (>5s), manual pause, and dense-concept detection (GPT-4o assesses video frame every 3 min); resumes video after quiz
- **Attention monitoring** — YOLOv8 webcam feed; flashes red after 20s face absence during video; triggers quiz on attention return; triggers quiz after 60s absence while reading
- **Handwritten answer OCR** — photo upload for open-ended questions; GPT-4o reads and grades the handwriting in one vision call
- **Paste detection** — tracks paste events on the answer input; sends `answer_pasted: true` to backend
- **"Prove It" follow-up** — when paste detected, GPT-4o generates a contextual follow-up the student must explain verbally to prove real comprehension
- **Shadow DOM isolation** — quiz overlay fully encapsulated; keyboard events blocked from leaking to YouTube/Khan Academy player

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
- OpenAI API key (optional — full deterministic fallback without it)

### 1. Clone and start all services

```bash
git clone https://github.com/DhairyaKakkar/DLHackathon.git
cd DLHackathon

# Optional: add your OpenAI key for LLM + vision features
# Edit docker-compose.yml → backend environment → OPENAI_API_KEY=sk-...
# Also set: USE_LLM_CONTEXT=true, USE_LLM_GRADING=true

docker compose up --build
```

Wait for: `INFO: Application startup complete.`

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| CompVis (YOLOv8) | http://localhost:8001 |

### 2. Install Chrome Extension

```bash
cd chrome-extension
python3 generate_icons.py
```

1. Chrome → `chrome://extensions` → Enable **Developer mode**
2. **Load unpacked** → select `chrome-extension/` folder
3. Click extension icon → **Options** → set Student API Key to `student-alice-key`

### 3. View Dashboards

- Student (Alice — fragile mastery): http://localhost:3000/student/1
- Student (Bob — overconfident): http://localhost:3000/student/2
- Faculty cohort view: http://localhost:3000/faculty

### 4. Test the Extension

Open `testbench/fake-lms.html` in Chrome — it contains Algorithms content that triggers keyword matching. Click the **EALE Check** button.

For video quiz: open any YouTube or Khan Academy video and rewind — the extension auto-pauses and shows a question.

Full grader walkthrough: **`testbench/SETUP.md`**

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://eale:eale_secret@localhost:5432/eale` | Postgres DSN |
| `OPENAI_API_KEY` | `` | OpenAI key (optional) |
| `OPENAI_MODEL` | `gpt-4o` | Model for question gen, grading, video assessment |
| `USE_LLM_CONTEXT` | `false` | Enable LLM question generation |
| `USE_LLM_GRADING` | `false` | Enable LLM grading + Prove It |
| `LLM_CACHE_TTL_SECONDS` | `300` | Question cache TTL (seconds) |
| `AUTO_SEED` | `true` | Seed demo data on startup |

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

## Running Tests

```bash
cd backend
PYTHONPATH=. python3.11 -m pytest tests/ -v
# 22 tests, < 1 second, no external dependencies (in-memory SQLite)
```

---

## Project Structure

```
DLHackathon/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, lifespan, routers
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── schemas.py               # Pydantic v2 schemas
│   │   ├── routers/
│   │   │   ├── extension.py         # Chrome extension endpoints
│   │   │   └── metrics.py           # Dashboard endpoints
│   │   └── services/
│   │       ├── metrics_service.py   # DUS + AI-dependency formula
│   │       ├── llm_service.py       # OpenAI integration (gen, grade, vision)
│   │       ├── scheduler_service.py # Spaced repetition scheduler
│   │       └── seed.py              # Demo data
│   └── tests/
├── chrome-extension/
│   ├── manifest.json                # MV3 manifest
│   ├── content.js                   # Shadow DOM overlay + all quiz logic
│   ├── background.js                # Screenshot capture, settings defaults
│   ├── options.html / options.js    # Extension settings page
│   └── popup.html / popup.js        # Extension popup
├── CompVis/                         # YOLOv8n inference service (Docker)
├── frontend/
│   └── src/app/
│       ├── student/[id]/            # Student dashboard
│       └── faculty/                 # Faculty cohort dashboard
├── testbench/
│   ├── SETUP.md                     # Step-by-step grader guide
│   ├── fake-lms.html                # Simulated LMS page for testing
│   ├── sample_curl.sh               # API curl examples
│   └── test_llm_mode.sh             # LLM flow end-to-end test
└── docker-compose.yml
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy (sync), psycopg2, APScheduler |
| Database | PostgreSQL 15 |
| AI / Vision | OpenAI GPT-4o (text + vision multimodal), YOLOv8n |
| Frontend | Next.js 14 App Router, TypeScript, Tailwind CSS, TanStack Query, Recharts |
| Extension | Chrome MV3, Shadow DOM, chrome.storage.sync |
| Config | Pydantic v2 + pydantic-settings |
| Infra | Docker Compose (4 services: db, backend, compvis, frontend) |
