# EALE — Evidence-Aligned Learning Engine

## Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy (sync), psycopg2-binary, APScheduler
- **Database**: PostgreSQL (Docker: `eale:eale_secret@localhost:5432/eale`)
- **Frontend**: Next.js 14 App Router, TypeScript, Tailwind CSS, TanStack Query, Recharts
- **Chrome Extension**: MV3, Shadow DOM overlay, chrome.storage.sync
- **Config**: Pydantic v2 + pydantic-settings

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

## Run Commands
```bash
# Start backend + DB
docker compose up --build -d db backend

# Start frontend
cd frontend && npm install && npm run dev

# Run tests
cd backend && PYTHONPATH=. python3.11 -m pytest tests/ -v

# Reset seed data
curl -X POST http://localhost:8000/api/v1/admin/reset
```

## Demo API Keys (seed data)
- Alice Chen (fragile mastery): `student-alice-key`
- Bob Martinez (overconfident): `student-bob-key`
- Dana Faculty: `faculty-dana-key`

## DUS Formula
```
DUS = 0.30 × mastery + 0.30 × retention + 0.25 × transfer + 0.15 × calibration
```

## Chrome Extension Setup
```bash
cd chrome-extension && python3 generate_icons.py
# Then: chrome://extensions → Developer mode → Load unpacked → chrome-extension/
```

## LLM Mode (optional)
Set in `docker-compose.yml` environment or shell:
```bash
USE_LLM_CONTEXT=true
USE_LLM_GRADING=true
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
```

## URLs
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000
- Fake LMS testbench: open `testbench/fake-lms.html` in Chrome
