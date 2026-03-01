#!/usr/bin/env bash
# EALE API — sample curl workflow
# Usage: bash testbench/sample_curl.sh
# Requires: curl, python3 (for pretty-printing)

BASE="http://localhost:8000/api/v1"
PP="python3 -m json.tool"

echo "============================================================"
echo "  EALE Testbench — Full Workflow Demo"
echo "============================================================"
echo ""

# ── 1. Health ─────────────────────────────────────────────────────────────────
echo "── 1. Health check"
curl -s http://localhost:8000/health | $PP
echo ""

# ── 2. List seeded students ───────────────────────────────────────────────────
echo "── 2. List students"
curl -s "$BASE/students/" | $PP
echo ""

# ── 3. List topics ────────────────────────────────────────────────────────────
echo "── 3. List topics"
curl -s "$BASE/topics/" | $PP
echo ""

# ── 4. List questions (originals only) ────────────────────────────────────────
echo "── 4. Original questions"
curl -s "$BASE/questions/?originals_only=true" | $PP
echo ""

# ── 5. Alice's dashboard (fragile mastery) ────────────────────────────────────
echo "── 5. Alice's student dashboard (expect: high mastery, poor transfer)"
curl -s "$BASE/metrics/student/1" | $PP
echo ""

# ── 6. Bob's dashboard (overconfident) ────────────────────────────────────────
echo "── 6. Bob's student dashboard (expect: high overconfidence_gap)"
curl -s "$BASE/metrics/student/2" | $PP
echo ""

# ── 7. Topic-level detail — Bob + Algorithms ──────────────────────────────────
echo "── 7. Bob × Algorithms topic metrics"
curl -s "$BASE/metrics/student/2/topic/3" | $PP
echo ""

# ── 8. Faculty cohort dashboard ───────────────────────────────────────────────
echo "── 8. Faculty dashboard"
curl -s "$BASE/metrics/faculty" | $PP
echo ""

# ── 9. Alice's due tasks ──────────────────────────────────────────────────────
echo "── 9. Alice's due tasks (retests + transfers)"
curl -s "$BASE/tasks/student/1" | $PP
echo ""

# ── 10. Submit a new attempt (Bob answers correctly) ─────────────────────────
echo "── 10. Bob submits a correct attempt on Q7 (binary search)"
curl -s -X POST "$BASE/attempts/" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": 2,
    "question_id": 7,
    "answer": "O(log n)",
    "confidence": 7,
    "reasoning": "Binary search halves the search space at each step"
  }' | $PP
echo ""

# ── 11. Generate variants for Q7 ─────────────────────────────────────────────
echo "── 11. Generate 2 deterministic variants for Q7 (binary search)"
curl -s -X POST "$BASE/questions/7/variants" \
  -H "Content-Type: application/json" \
  -d '{"num_variants": 2, "use_llm": false}' | $PP
echo ""

# ── 12. Create a new student + full mini-flow ────────────────────────────────
echo "── 12. Create new student 'Charlie'"
STUDENT_JSON=$(curl -s -X POST "$BASE/students/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Charlie Dev", "email": "charlie@example.com"}')
echo "$STUDENT_JSON" | $PP
STUDENT_ID=$(echo "$STUDENT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  → Charlie's ID: $STUDENT_ID"
echo ""

echo "── 12b. Charlie submits attempt on Q1 (len([1,2,3]))"
curl -s -X POST "$BASE/attempts/" \
  -H "Content-Type: application/json" \
  -d "{
    \"student_id\": $STUDENT_ID,
    \"question_id\": 1,
    \"answer\": \"3\",
    \"confidence\": 9
  }" | $PP
echo ""

echo "── 12c. Charlie's future tasks (scheduler just created them)"
curl -s "$BASE/tasks/student/$STUDENT_ID?include_future=true" | $PP
echo ""

# ── 13. Manually trigger scheduler ───────────────────────────────────────────
echo "── 13. Trigger scheduler tick manually"
curl -s -X POST "$BASE/admin/scheduler/run" | $PP
echo ""

echo "============================================================"
echo "  Done! Visit http://localhost:8000/docs for full API."
echo "============================================================"
