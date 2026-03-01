# EALE Grader Guide — Testbench

This guide walks a grader through starting the system and exercising all major
API flows end-to-end, including reproducing the "fragile mastery" pattern.

---

## 1. Start the System

### Option A — Docker Compose (recommended)

```bash
cd /path/to/DLHackathon
docker compose up --build
```

Wait until you see:
```
backend_1  | INFO:     Application startup complete.
```

The API is now live at **http://localhost:8000**.
Interactive docs: **http://localhost:8000/docs**

### Option B — Local (no Docker)

Prerequisites: Python 3.11+, PostgreSQL running locally.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set DATABASE_URL to your local Postgres
export DATABASE_URL="postgresql://eale:eale_secret@localhost:5432/eale"
export AUTO_SEED=true

uvicorn app.main:app --reload --port 8000
```

---

## 2. Verify Health

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
# Expected: {"status": "ok"}
```

---

## 3. Explore Pre-Seeded Data

The system seeds two students, three topics, 14 questions, and 30+ attempts
on startup. No manual setup required.

```bash
# List students
curl -s http://localhost:8000/api/v1/students/ | python3 -m json.tool

# List topics
curl -s http://localhost:8000/api/v1/topics/ | python3 -m json.tool

# List all questions (originals + variants)
curl -s http://localhost:8000/api/v1/questions/ | python3 -m json.tool
```

Seed API keys:
| User         | api_key               | Role    |
|--------------|-----------------------|---------|
| Alice Chen   | `student-alice-key`   | student |
| Bob Martinez | `student-bob-key`     | student |
| Dana Faculty | `faculty-dana-key`    | faculty |

---

## 4. Student Dashboard — "Fragile Mastery" (Alice)

Alice has high mastery on original questions but fails variants (poor transfer).
She also shows a retention drop in Algorithms after 3 days.

```bash
curl -s http://localhost:8000/api/v1/metrics/student/1 | python3 -m json.tool
```

**What to look for:**
- `mastery` ≈ 80–100 on Python Basics / Data Structures
- `transfer_robustness` ≈ 0–35 (she fails variants)
- `retention` drops on Algorithms (≈ 55–65)
- `durable_understanding_score` significantly below mastery

---

## 5. Student Dashboard — "Overconfident" (Bob)

Bob submits high confidence (8–9/10) but is mostly wrong on DS and Algorithms.

```bash
curl -s http://localhost:8000/api/v1/metrics/student/2 | python3 -m json.tool
```

**What to look for:**
- `overconfidence_gap` > 30 pp on Data Structures + Algorithms
- `calibration` < 30 on those topics
- `mastery` < 20 on Algorithms
- `durable_understanding_score` < 25

---

## 6. Topic-Level Metrics

```bash
# Alice + Python Basics (topic 1)
curl -s http://localhost:8000/api/v1/metrics/student/1/topic/1 | python3 -m json.tool

# Bob + Algorithms (topic 3)
curl -s http://localhost:8000/api/v1/metrics/student/2/topic/3 | python3 -m json.tool
```

Each response includes:
- `retention_bins`: accuracy per time-gap bucket (same_day, day_1_3, day_3_7, week_plus)
- `calibration_bins`: ECE breakdown per confidence bin
- `*_explanation`: human-readable deterministic explanation

---

## 7. Faculty Cohort Dashboard

```bash
curl -s http://localhost:8000/api/v1/metrics/faculty | python3 -m json.tool
```

**What to look for:**
- `low_retention_topics`: topics where cohort retention < 60
- `transfer_failure_topics`: topics where cohort transfer < 60
- `overconfidence_hotspots`: topics with avg overconfidence gap > 15 pp
- `dus_distribution`: histogram of DUS values across all student-topic pairs

---

## 8. Due Tasks for a Student

```bash
# Alice's due tasks (overdue retests + transfers)
curl -s "http://localhost:8000/api/v1/tasks/student/1" | python3 -m json.tool

# Include future tasks
curl -s "http://localhost:8000/api/v1/tasks/student/1?include_future=true" | python3 -m json.tool
```

---

## 9. Submit a New Attempt

```bash
# Bob attempts Q7 (binary search) correctly this time
curl -s -X POST http://localhost:8000/api/v1/attempts/ \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": 2,
    "question_id": 7,
    "answer": "O(log n)",
    "confidence": 6,
    "reasoning": "I reviewed my notes — binary search halves the search space each step"
  }' | python3 -m json.tool
```

The response includes `is_correct: true/false`.
After submission, the scheduler immediately creates follow-up RETEST tasks.

---

## 10. Generate Variants for a Question

```bash
# Generate 2 deterministic variants for question 7 (binary search)
curl -s -X POST http://localhost:8000/api/v1/questions/7/variants \
  -H "Content-Type: application/json" \
  -d '{"num_variants": 2, "use_llm": false}' | python3 -m json.tool
```

---

## 11. Create a New Student + Submit Attempt (Full Flow)

```bash
# Create student
STUDENT=$(curl -s -X POST http://localhost:8000/api/v1/students/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Student", "email": "test@example.com"}')
echo $STUDENT | python3 -m json.tool

STUDENT_ID=$(echo $STUDENT | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Submit attempt
curl -s -X POST http://localhost:8000/api/v1/attempts/ \
  -H "Content-Type: application/json" \
  -d "{
    \"student_id\": $STUDENT_ID,
    \"question_id\": 1,
    \"answer\": \"3\",
    \"confidence\": 8
  }" | python3 -m json.tool

# Check due tasks (scheduler creates them immediately)
curl -s "http://localhost:8000/api/v1/tasks/student/$STUDENT_ID?include_future=true" | python3 -m json.tool
```

---

## 12. Reset and Reseed

```bash
curl -s -X POST http://localhost:8000/api/v1/admin/reset | python3 -m json.tool
```

⚠️ This drops all tables and re-runs the full seed — useful to restore the demo state.

---

## 13. Run Unit Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

Expected: all tests pass in < 5 seconds (in-memory SQLite, no external dependencies).

---

## Expected Response Shapes

### Student Dashboard excerpt
```json
{
  "student_id": 1,
  "student_name": "Alice Chen",
  "overall_dus": 47.3,
  "topics": [
    {
      "topic_name": "Python Basics",
      "mastery": 83.0,
      "retention": 88.0,
      "transfer_robustness": 18.0,
      "calibration": 71.0,
      "durable_understanding_score": 58.9,
      "dus_formula": "DUS = 0.30 × mastery + 0.30 × retention + 0.25 × transfer + 0.15 × calibration",
      "transfer_explanation": "Transfer is poor: only 18% on variants vs 83% on originals — student may have memorised surface form rather than the underlying concept."
    }
  ]
}
```

### Faculty Dashboard excerpt
```json
{
  "num_students": 2,
  "transfer_failure_topics": ["Python Basics", "Data Structures", "Algorithms"],
  "overconfidence_hotspots": ["Data Structures", "Algorithms"],
  "dus_distribution": [
    {"label": "0-20", "count": 2, "avg_value": 14.5},
    {"label": "20-40", "count": 1, "avg_value": 31.0},
    {"label": "40-60", "count": 2, "avg_value": 51.2},
    {"label": "60-80", "count": 1, "avg_value": 63.4}
  ]
}
```
