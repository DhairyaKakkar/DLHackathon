# Evidence-Aligned Learning Engine (EALE)

EALE measures whether a student's learning is **durable** — not just whether they can
answer a question once, but whether they can answer it:

- After a **time gap** (Retention)
- In a **different surface form** (Transfer)
- With **calibrated confidence** (Calibration)

These three evidence dimensions are combined into a single **Durable Understanding Score (DUS)**.

---

## Architecture

```
FastAPI + SQLAlchemy (sync)   →  PostgreSQL
APScheduler BackgroundScheduler  →  spaced-retest task creation
Deterministic variant generator  →  (optional) OpenAI LLM variant generation
```

### Data Model

| Table            | Purpose                                          |
|------------------|--------------------------------------------------|
| `students`       | Users (student or faculty role + API key)        |
| `topics`         | Concept/topic buckets                            |
| `questions`      | Original questions (MCQ or SHORT_TEXT)           |
| `questions`*     | Variant questions (`is_variant=true`, linked)    |
| `attempts`       | Student answers + confidence + correctness       |
| `scheduled_tasks`| Spaced-retest and transfer-task queue            |

---

## Metric Formulas

### Component Scores (all 0–100)

**Mastery**
```
mastery = (correct / total) × 100   [last 10 original-question attempts]
```

**Retention**
```
Bin attempts by time gap from first attempt on each question:
  same_day  (0–24 h)
  day_1_3   (24–72 h)
  day_3_7   (72–168 h)
  week_plus (168+ h)

baseline_acc = avg(same_day, day_1_3)
later_acc    = avg(day_3_7, week_plus)
drop         = max(0, baseline_acc − later_acc)
retention    = 100 × (1 − drop × 1.5)          [capped 0–100]
```

**Transfer Robustness**
```
transfer = (variant_accuracy / original_accuracy) × 100   [capped 0–100]
```

**Calibration** (ECE-like)
```
Confidence bins: [1-2], [3-4], [5-6], [7-8], [9-10]
For each bin:
  bin_error = |mean_confidence/10 − bin_accuracy|
ECE = Σ (bin_count / total) × bin_error
calibration = 100 × (1 − ECE)
```

### Durable Understanding Score (DUS)

```
DUS = 0.30 × mastery
    + 0.30 × retention
    + 0.25 × transfer_robustness
    + 0.15 × calibration
```

DUS of 80+ = durable. 60–79 = partial. Below 60 = fragile mastery.

---

## Quick Start

### One-command run (Docker)

```bash
git clone <repo>
cd DLHackathon
docker compose up --build
```

API: http://localhost:8000
Docs: http://localhost:8000/docs

### Local run (no Docker)

```bash
# 1. Start Postgres
createdb eale
createuser eale -P   # password: eale_secret

# 2. Install deps
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp ../.env.example .env
# Edit .env: set DATABASE_URL

# 4. Run
uvicorn app.main:app --reload --port 8000
```

The app **auto-creates tables and seeds demo data** on first boot.

### Reset demo data

```bash
curl -X POST http://localhost:8000/api/v1/admin/reset
```

### Run tests

```bash
cd backend
pytest tests/ -v
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/students/` | Create student |
| GET | `/students/` | List students |
| GET | `/students/{id}` | Get student |
| POST | `/topics/` | Create topic |
| GET | `/topics/` | List topics |
| POST | `/questions/` | Create question |
| GET | `/questions/` | List questions (filter: `topic_id`, `originals_only`, `variants_only`) |
| POST | `/questions/{id}/variants` | Generate variants (deterministic or LLM) |
| GET | `/questions/{id}/variants` | List existing variants |
| POST | `/attempts/` | Submit attempt (answer + confidence) |
| GET | `/attempts/` | List attempts (filter: `student_id`, `question_id`) |
| GET | `/tasks/student/{id}` | Due tasks for student |
| GET | `/tasks/` | All pending tasks |
| GET | `/metrics/student/{id}` | Student dashboard (all topics) |
| GET | `/metrics/student/{id}/topic/{tid}` | Single topic metrics |
| GET | `/metrics/faculty` | Faculty cohort dashboard |
| POST | `/admin/seed` | Seed (no-op if seeded) |
| POST | `/admin/reset` | ⚠️ Reset + reseed |
| POST | `/admin/scheduler/run` | Trigger scheduler tick |

Full interactive docs at `/docs` (Swagger) or `/redoc`.

---

## Seed Data

On first run, the system seeds:

- **Alice Chen** (`student-alice-key`) — High mastery, poor transfer. Memorises surface form.
- **Bob Martinez** (`student-bob-key`) — Severely overconfident. High confidence, low accuracy.
- **Dana Faculty** (`faculty-dana-key`) — Faculty role for cohort view.

- 3 Topics: Python Basics, Data Structures, Algorithms
- 14 Questions (8 originals + 6 variants with different phrasings/contexts)
- 30+ Attempts with realistic timestamps demonstrating all metric patterns

---

## LLM Variant Generation (optional)

```bash
# In .env:
USE_LLM_VARIANTS=true
OPENAI_API_KEY=sk-...
```

Then:
```bash
curl -X POST http://localhost:8000/api/v1/questions/7/variants \
  -H "Content-Type: application/json" \
  -d '{"num_variants": 2, "use_llm": true}'
```

Falls back to deterministic templates if the API call fails.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://eale:eale_secret@localhost:5432/eale` | Postgres DSN |
| `AUTO_SEED` | `true` | Auto-seed on startup |
| `USE_LLM_VARIANTS` | `false` | Enable OpenAI variant generation |
| `OPENAI_API_KEY` | `` | OpenAI API key (optional) |
| `CORS_ORIGINS` | `*` | Comma-separated or `*` |
| `SCHEDULER_INTERVAL_SECONDS` | `60` | How often the scheduler runs |

---

## Example curl Commands

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Student dashboard (fragile mastery — Alice)
curl http://localhost:8000/api/v1/metrics/student/1

# 3. Student dashboard (overconfident — Bob)
curl http://localhost:8000/api/v1/metrics/student/2

# 4. Faculty cohort dashboard
curl http://localhost:8000/api/v1/metrics/faculty

# 5. Alice's due tasks
curl http://localhost:8000/api/v1/tasks/student/1

# 6. Submit attempt
curl -X POST http://localhost:8000/api/v1/attempts/ \
  -H "Content-Type: application/json" \
  -d '{"student_id":2,"question_id":7,"answer":"O(log n)","confidence":7}'

# 7. Generate variants
curl -X POST http://localhost:8000/api/v1/questions/7/variants \
  -H "Content-Type: application/json" \
  -d '{"num_variants":2,"use_llm":false}'

# 8. Create topic
curl -X POST http://localhost:8000/api/v1/topics/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Graph Theory","description":"Graphs, DFS, BFS, shortest paths"}'

# 9. Create question
curl -X POST http://localhost:8000/api/v1/questions/ \
  -H "Content-Type: application/json" \
  -d '{"topic_id":1,"text":"What does `type(True)` return?","question_type":"MCQ","difficulty":2,"correct_answer":"bool","options":["int","bool","str","float"]}'

# 10. Reset demo data
curl -X POST http://localhost:8000/api/v1/admin/reset
```

---

## Migrations (Alembic)

The app uses `create_all` on startup for zero-friction demo runs.
For production-style migration management:

```bash
cd backend
# Generate a new migration
alembic revision --autogenerate -m "add_new_column"
# Apply migrations
alembic upgrade head
# Rollback
alembic downgrade -1
```

The initial migration is in `alembic/versions/0001_initial_schema.py`.
