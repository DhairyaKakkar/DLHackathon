# EALE — Evidence-Aligned Learning Engine

## Project Overview

EALE measures whether a student's learning is **durable** — not just answering once, but:
- After a **time gap** (Retention)
- In a **different surface form** (Transfer)
- With **calibrated confidence** (Calibration)

These combine into a single **Durable Understanding Score (DUS)**.

```
DUS = 0.30 × mastery + 0.30 × retention + 0.25 × transfer + 0.15 × calibration
```

DUS 80+: Durable | 60–79: Partial | <60: Fragile mastery

---

## Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy (sync), psycopg2-binary, APScheduler
- **Database**: PostgreSQL (Docker: `eale:eale_secret@localhost:5432/eale`)
- **Frontend**: Next.js 14 App Router, TypeScript, Tailwind CSS, TanStack Query, Recharts
- **Chrome Extension**: MV3, Shadow DOM overlay, chrome.storage.sync
- **Config**: Pydantic v2 + pydantic-settings
- **LLM (optional)**: OpenAI `gpt-4.1-mini` — feature-flagged, fails gracefully to deterministic fallbacks

---

## Project Structure

```
DLHackathon/
├── backend/app/
│   ├── main.py               # FastAPI app, lifespan hooks
│   ├── config.py             # Pydantic settings from env
│   ├── database.py           # SQLAlchemy engine + Base
│   ├── models.py             # ORM: Student, Topic, Question, Attempt, ScheduledTask
│   ├── schemas.py            # Pydantic I/O schemas
│   ├── routers/              # students, topics, questions, attempts, tasks, metrics, admin, extension
│   └── services/
│       ├── llm_service.py        # OpenAI gen + grading (USE_LLM_* flags)
│       ├── metrics_service.py    # DUS formula computations
│       ├── scheduler_service.py  # APScheduler spaced-retest/transfer tasks
│       ├── seed.py               # Demo data seeding
│       └── variant_generator.py  # Deterministic question variants
├── frontend/src/app/
│   ├── page.tsx              # Landing page
│   ├── student/[id]/         # Student DUS dashboard
│   └── faculty/              # Faculty cohort view
├── chrome-extension/
│   ├── manifest.json         # MV3 manifest
│   ├── popup.html/js         # Quiz overlay UI
│   ├── background.js         # Service worker (alarms)
│   ├── content.js            # Page content extraction + Shadow DOM quiz
│   └── options.html/js       # Student ID + API URL config
├── testbench/                # Fake LMS HTML test page
└── docker-compose.yml        # Postgres + backend + frontend
```

---

## Key Paths
- `backend/app/main.py` — FastAPI app, lifespan (tables + seed + scheduler)
- `backend/app/models.py` — SQLAlchemy models (Student, Topic, Question, Attempt, ScheduledTask)
- `backend/app/services/metrics_service.py` — DUS formula computations
- `backend/app/services/seed.py` — Demo data seed
- `backend/app/services/scheduler_service.py` — APScheduler spaced-retest logic
- `backend/app/services/llm_service.py` — OpenAI question gen + grading (feature-flagged)
- `backend/app/routers/extension.py` — Chrome extension endpoints
- `chrome-extension/content.js` — Shadow DOM quiz overlay (state machine)
- `frontend/src/` — Next.js pages and components

---

## Data Models

| Model | Key Fields |
|---|---|
| `Student` | `id`, `name`, `email`, `api_key`, `role` (student/faculty) |
| `Topic` | `id`, `name`, `description` |
| `Question` | `id`, `topic_id`, `text`, `question_type` (MCQ/SHORT_TEXT), `difficulty` (1-5), `is_variant`, `original_question_id` |
| `Attempt` | `id`, `student_id`, `question_id`, `answer`, `confidence` (1-10), `is_correct`, `created_at` |
| `ScheduledTask` | `id`, `student_id`, `question_id`, `task_type` (RETEST/TRANSFER), `due_at`, `completed_at` |

---

## Run Commands
```bash
# Start backend + DB
docker compose up --build -d db backend

# Start frontend
cd frontend && npm install && npm run dev

# Full stack
docker compose up --build

# Run tests
cd backend && PYTHONPATH=. python3.11 -m pytest tests/ -v

# Reset seed data
curl -X POST http://localhost:8000/api/v1/admin/reset
```

---

## Demo API Keys (seed data)
- **Alice Chen** (id=1, fragile mastery, DUS ~47): `student-alice-key`
- **Bob Martinez** (id=2, overconfident, DUS ~18): `student-bob-key`
- **Dana Faculty**: `faculty-dana-key`
- 3 Topics: Python Basics, Data Structures, Algorithms
- 14 Questions (8 originals + 6 variants)

---

## Key API Endpoints (base: `/api/v1`)

| Method | Path | Description |
|---|---|---|
| GET | `/metrics/student/{id}` | Full DUS dashboard |
| GET | `/metrics/faculty` | Cohort view |
| POST | `/attempts/` | Submit answer + confidence |
| POST | `/questions/{id}/variants` | Generate variants |
| GET | `/tasks/student/{id}` | Due retest/transfer tasks |
| POST | `/extension/context` | Chrome ext: best question for page |
| POST | `/extension/submit` | Chrome ext: submit answer |
| POST | `/admin/reset` | Reset + reseed demo data |

---

## Chrome Extension Setup
```bash
cd chrome-extension && python3 generate_icons.py
# Then: chrome://extensions → Developer mode → Load unpacked → chrome-extension/
```

---

## LLM Mode (optional)
Set in `docker-compose.yml` environment or shell:
```bash
USE_LLM_CONTEXT=true     # LLM picks question based on page content
USE_LLM_GRADING=true     # LLM grades SHORT_TEXT answers
USE_LLM_VARIANTS=true    # LLM generates question variants
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
```
All LLM paths fail gracefully to deterministic fallbacks. LLM responses are cached (SHA-256 key, 600s TTL).

---

## Extension Question Selection Priority
1. Overdue scheduled task (RETEST / TRANSFER)
2. LLM path (if `USE_LLM_CONTEXT=true` + key set + not rate-limited)
3. Keyword match against `TOPIC_KEYWORD_MAP` in `extension.py`
4. Random fallback

---

## URLs
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000
- Fake LMS testbench: open `testbench/fake-lms.html` in Chrome
