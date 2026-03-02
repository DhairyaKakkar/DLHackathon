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
- Frontend: http://localhost:3001
- Fake LMS testbench: open `testbench/fake-lms.html` in Chrome

---

## Installed Claude Code Plugins

### superpowers v4.3.1 — `obra/superpowers-marketplace`

Framework of proven development skills. The SessionStart hook auto-injects context at the start of every conversation.

**When to invoke each skill:**

| Skill | When to use |
|---|---|
| `brainstorming` | **Before any creative work** — features, components, new functionality. Uses Socratic dialogue. Has a hard gate: no code until design is approved. |
| `writing-plans` | When you have requirements for a multi-step task, before touching code. Produces 2–5 min bite-sized tasks. |
| `executing-plans` | When executing a written plan in the current session with review checkpoints. |
| `test-driven-development` | Before writing any implementation code. Enforces RED (failing test) → GREEN (pass) → REFACTOR cycle. |
| `systematic-debugging` | Before proposing any fix for a bug, test failure, or unexpected behavior. Four-phase root cause analysis. |
| `verification-before-completion` | Before claiming work is done, fixed, or passing. Runs verification commands, evidence before assertions. |
| `requesting-code-review` | After completing a task or feature, before merging. Pre-review quality checklist. |
| `receiving-code-review` | When processing code review feedback. Requires technical rigor, not blind agreement. |
| `subagent-driven-development` | When executing independent tasks in the current session using subagents with two-stage review. |
| `dispatching-parallel-agents` | When facing 2+ independent tasks with no shared state. Runs them concurrently. |
| `using-git-worktrees` | Before feature work needing isolation, or before executing implementation plans. |
| `finishing-a-development-branch` | When implementation is complete and tests pass. Guides merge/PR/cleanup decisions. |
| `writing-skills` | When creating or editing custom skills. |
| `using-superpowers` | At session start — establishes skill discovery and usage framework. |

**Commands:**
- `/brainstorm` — Refines requirements via Socratic dialogue before any implementation
- `/write-plan` — Decomposes work into precise, bite-sized tasks
- `/execute-plan` — Deploys subagents or batch processing with staged reviews

**Install:**
```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

---

### frontend-design — `claude-plugins-official`

Creates distinctive, production-grade frontend interfaces. Auto-activates when building web components, pages, or UIs. Explicitly fights generic "AI slop" aesthetics.

**What it does:**
- Commits to a **bold aesthetic direction** before writing any code (brutalist, maximalist, retro-futuristic, luxury, editorial, organic, etc.)
- Enforces distinctive typography (never Inter/Arial/Roboto — use characterful display fonts)
- Requires cohesive color palettes with dominant colors + sharp accents
- Mandates high-impact animations and micro-interactions (CSS-first, Motion library for React)
- Uses unexpected spatial composition: asymmetry, overlap, diagonal flow, grid-breaking elements
- Adds depth via gradient meshes, noise textures, geometric patterns, layered transparencies

**Critical rules it enforces:**
- Never use purple gradients on white backgrounds
- Never use Space Grotesk, Inter, or system fonts as primary choices
- Every design must be memorable and context-specific — no two should look alike
- Match implementation complexity to aesthetic vision: maximalist = elaborate animations, minimalist = precise restraint

**Relevant for this project:** Chrome extension overlay redesign, frontend dashboard pages, any new UI components.

**Install:**
```bash
/plugin install frontend-design@claude-plugins-official
```
