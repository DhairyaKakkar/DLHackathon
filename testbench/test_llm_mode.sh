#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# EALE LLM Mode Testbench
#
# Tests three flows:
#   1) Deterministic fallback  (LLM disabled — always works)
#   2) LLM context + question generation  (needs USE_LLM_CONTEXT=true + OPENAI_API_KEY)
#   3) LLM short-answer grading  (needs USE_LLM_GRADING=true + OPENAI_API_KEY)
#
# Usage:
#   # Deterministic only (no key needed):
#   bash testbench/test_llm_mode.sh
#
#   # Full LLM mode:
#   OPENAI_API_KEY=sk-... USE_LLM_CONTEXT=true USE_LLM_GRADING=true \
#     bash testbench/test_llm_mode.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BASE="http://localhost:8000/api/v1"
ALICE="student-alice-key"

ECON_SNIPPET="Macroeconomics studies economy-wide phenomena such as inflation, \
unemployment, and GDP growth. The aggregate demand and supply model determines \
the price level and output. Fiscal policy involves government spending and \
taxation to influence the economy. Monetary policy is conducted by central \
banks to control money supply and interest rates. The Phillips curve shows \
the short-run trade-off between inflation and unemployment. \
Quantitative easing is a tool used when interest rates are at the zero lower bound."

SEP="────────────────────────────────────────────────────────────────────────────"

echo ""
echo "$SEP"
echo " EALE LLM Mode Testbench"
echo " Backend: $BASE"
echo " USE_LLM_CONTEXT=${USE_LLM_CONTEXT:-false}  USE_LLM_GRADING=${USE_LLM_GRADING:-false}"
echo "$SEP"


# ── Test 1: Deterministic fallback ────────────────────────────────────────────
echo ""
echo "TEST 1 — Deterministic fallback (keyword match / random)"
echo "$SEP"

RESP1=$(curl -s -X POST "$BASE/extension/context" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ALICE" \
  -d "{
    \"page_url\": \"http://localhost/test\",
    \"page_title\": \"Introduction to Sorting Algorithms\",
    \"page_text\": \"Binary search runs in O(log n) time. Merge sort is a divide and conquer algorithm.\"
  }")

echo "$RESP1" | python3 -m json.tool
MODE1=$(echo "$RESP1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('mode','?'))")
echo ""
echo "  → mode: $MODE1  (expected: KEYWORD or DUE_TASK)"


# ── Test 2: LLM context + question generation ─────────────────────────────────
echo ""
echo "TEST 2 — LLM context (Economics page snippet)"
echo "$SEP"

RESP2=$(curl -s -X POST "$BASE/extension/context" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ALICE" \
  -d "{
    \"page_url\": \"https://coursera.org/learn/macro-economics/week3\",
    \"page_title\": \"Macroeconomics: Aggregate Demand and Monetary Policy\",
    \"page_text\": \"$ECON_SNIPPET\"
  }")

echo "$RESP2" | python3 -m json.tool
MODE2=$(echo "$RESP2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('mode','?'))")
Q_ID=$(echo  "$RESP2" | python3 -c "import sys,json; print(json.load(sys.stdin)['question']['id'])")
Q_TYPE=$(echo "$RESP2" | python3 -c "import sys,json; print(json.load(sys.stdin)['question']['question_type'])")
echo ""
echo "  → mode: $MODE2  question_id: $Q_ID  type: $Q_TYPE"

if [ "$MODE2" = "LLM" ]; then
  echo "  ✓  LLM context generation working"
else
  echo "  ℹ  LLM not active — got $MODE2 (set USE_LLM_CONTEXT=true to enable)"
fi


# ── Test 3: LLM short-answer grading ─────────────────────────────────────────
echo ""
echo "TEST 3 — Submit answer + grading  (question_id=$Q_ID, type=$Q_TYPE)"
echo "$SEP"

if [ "$Q_TYPE" = "SHORT_TEXT" ]; then
  ANSWER="Fiscal policy uses government spending and taxation to stimulate or slow the economy, affecting aggregate demand and employment levels."
else
  # For MCQ, grab the correct answer from the context response
  ANSWER=$(echo "$RESP2" | python3 -c "
import sys, json
d = json.load(sys.stdin)
q = d['question']
# Use correct_answer directly
print(q['correct_answer'])
")
fi

RESP3=$(curl -s -X POST "$BASE/extension/submit" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ALICE" \
  -d "{
    \"question_id\": $Q_ID,
    \"answer\": \"$ANSWER\",
    \"confidence\": 7
  }")

echo "$RESP3" | python3 -m json.tool
CORRECT=$(echo "$RESP3" | python3 -c "import sys,json; print(json.load(sys.stdin)['correct'])")
DUS=$(echo "$RESP3" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('updated_dus','N/A'))")
echo ""
echo "  → correct: $CORRECT   updated_dus: $DUS"

if [ "${USE_LLM_GRADING:-false}" = "true" ]; then
  echo "  ✓  LLM grading active (score ≥ 0.7 = correct)"
else
  echo "  ℹ  Deterministic grading (set USE_LLM_GRADING=true to enable LLM rubric)"
fi


echo ""
echo "$SEP"
echo " Done."
echo "$SEP"
echo ""
