"""
Extension endpoints — serve micro-quiz questions and accept submissions
from the EALE Chrome Extension.

POST /api/v1/extension/context  → pick best question for the current page
POST /api/v1/extension/submit   → record attempt, return feedback + updated DUS

Question-selection priority (/context):
  1. LLM path (if USE_LLM_CONTEXT=true + OPENAI_API_KEY set + student not rate-limited)
  2. Overdue scheduled task (RETEST / TRANSFER) — when LLM is disabled or fails
  3. Keyword-match against TOPIC_KEYWORD_MAP
  4. Random fallback

Grading (/submit, SHORT_TEXT only):
  - If USE_LLM_GRADING=true + OPENAI_API_KEY set → LLM rubric grader (score ≥ 0.7 = correct)
  - Else → deterministic substring match (unchanged behaviour)
"""

import random
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config import settings
from app.database import get_db
from app.models import (
    Attempt, Question, ScheduledTask, Student, Topic,
    QuestionType, TaskType,
)
from app.schemas import QuestionOut
from app.services.scheduler_service import mark_completed_tasks, schedule_follow_ups
from app.services.metrics_service import load_student_topic_metrics

router = APIRouter(prefix="/extension", tags=["Extension"])


# ─── Topic → keyword map (deterministic fallback) ────────────────────────────

TOPIC_KEYWORD_MAP: dict[str, list[str]] = {
    "Python Basics": [
        "python", "def ", "for loop", "while loop", "list comprehension",
        "dictionary", "import", "print(", "function", "variable", "class ",
        "indentation", "tuple", "string format", "lambda",
    ],
    "Data Structures": [
        "stack", "queue", "lifo", "fifo", "linked list", "binary tree",
        "heap", "hash table", "graph", "node", "pointer", "deque",
        "adjacency", "traversal", "balanced tree",
    ],
    "Algorithms": [
        "sort", "binary search", "log n", "big o", "time complexity",
        "space complexity", "recursion", "dynamic programming", "greedy",
        "breadth-first", "depth-first", "bfs", "dfs", "algorithm",
        "divide and conquer", "memoization", "iteration",
    ],
}


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ExtensionContextRequest(BaseModel):
    page_url: str = ""
    page_title: str = ""
    page_text: str = ""       # first ~2 000 chars of visible page text


class ExtensionContextOut(BaseModel):
    task_id: Optional[int]
    task_type: Optional[str]
    topic_name: str
    question: QuestionOut
    rationale: str
    mode: str                 # "DUE_TASK" | "LLM" | "KEYWORD" | "RANDOM"


class ExtensionSubmitRequest(BaseModel):
    question_id: int
    task_id: Optional[int] = None
    answer: str
    confidence: int           # 1–10
    reasoning: Optional[str] = None


class ExtensionSubmitOut(BaseModel):
    correct: bool
    feedback: str
    correct_answer: str
    explanation: str
    updated_dus: Optional[float] = None   # overall DUS after this attempt


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_student(api_key: str, db: Session) -> Student:
    student = db.query(Student).filter(Student.api_key == api_key).first()
    if not student:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return student


def _infer_topic_keyword(page_text: str, db: Session) -> Optional[Topic]:
    lowered = page_text.lower()
    scores = {
        name: sum(1 for kw in kws if kw in lowered)
        for name, kws in TOPIC_KEYWORD_MAP.items()
    }
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return None
    return db.query(Topic).filter(Topic.name == best).first()


def _pick_unanswered(student_id: int, topic_id: int, db: Session) -> Optional[Question]:
    answered = {
        r[0] for r in
        db.query(Attempt.question_id).filter(Attempt.student_id == student_id).all()
    }
    candidates = (
        db.query(Question)
          .filter(Question.topic_id == topic_id, Question.is_variant.is_(False))
          .all()
    )
    pool = [q for q in candidates if q.id not in answered] or candidates
    return random.choice(pool) if pool else None


def _pick_any_question(student_id: int, db: Session) -> Optional[Question]:
    answered = {
        r[0] for r in
        db.query(Attempt.question_id).filter(Attempt.student_id == student_id).all()
    }
    originals = db.query(Question).filter(Question.is_variant.is_(False)).all()
    pool = [q for q in originals if q.id not in answered] or originals
    return random.choice(pool) if pool else None


def _check_correctness_deterministic(question: Question, answer: str) -> bool:
    correct = question.correct_answer.strip().lower()
    given = answer.strip().lower()
    if question.question_type == QuestionType.MCQ:
        return given == correct
    return correct in given or given in correct


def _compute_overall_dus(db: Session, student_id: int) -> Optional[float]:
    try:
        metrics = load_student_topic_metrics(db, student_id)
        if not metrics:
            return None
        return round(
            sum(t["durable_understanding_score"] for t in metrics) / len(metrics), 1
        )
    except Exception:
        return None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/context", response_model=ExtensionContextOut)
def get_extension_context(
    payload: ExtensionContextRequest,
    x_api_key: str = Header(..., description="Student API key"),
    db: Session = Depends(get_db),
):
    """
    Select the best question for the current learning page.

    Priority:
      1. LLM-generated question (if USE_LLM_CONTEXT=true) — page context first
      2. Overdue scheduled task (when LLM disabled or fails)
      3. Keyword-matched question from existing bank
      4. Random question fallback
    """
    student = _get_student(x_api_key, db)

    # ── 1: LLM path (when enabled, always runs first — page context drives the question) ──
    if settings.USE_LLM_CONTEXT and settings.OPENAI_API_KEY:
        from app.services.llm_service import (
            infer_topic_and_generate_question,
            is_rate_limited,
            record_llm_call,
        )

        if not is_rate_limited(student.id):
            llm_result = infer_topic_and_generate_question(
                url=payload.page_url,
                title=payload.page_title,
                text_snippet=payload.page_text,
            )

            if llm_result:
                record_llm_call(student.id)

                # Get or create the topic
                topic = db.query(Topic).filter(Topic.name == llm_result.topic_name).first()
                if not topic:
                    topic = Topic(
                        name=llm_result.topic_name,
                        description=f"Auto-created by EALE LLM ({settings.OPENAI_MODEL})",
                    )
                    db.add(topic)
                    db.flush()

                # Determine stored fields
                if llm_result.question_type == "MCQ":
                    q_type = QuestionType.MCQ
                    correct_ans = llm_result.correct_option or ""
                    stored_options = llm_result.options
                else:
                    q_type = QuestionType.SHORT_TEXT
                    # Primary answer = first rubric criterion; rubric stored in options
                    rubric = llm_result.rubric or []
                    correct_ans = rubric[0] if rubric else llm_result.question_text
                    stored_options = rubric  # reuse options field for rubric list

                question = Question(
                    topic_id=topic.id,
                    text=llm_result.question_text,
                    question_type=q_type,
                    difficulty=llm_result.difficulty,
                    correct_answer=correct_ans,
                    options=stored_options,
                    is_variant=False,
                    variant_template="LLM_CONTEXT",  # source tag
                )
                db.add(question)
                db.commit()
                db.refresh(question)

                return ExtensionContextOut(
                    task_id=None,
                    task_type=None,
                    topic_name=topic.name,
                    question=QuestionOut.model_validate(question),
                    rationale=llm_result.rationale,
                    mode="LLM",
                )
        # Rate-limited or LLM failed — fall through to due tasks / keyword / random

    # ── 2: Due tasks (when LLM is disabled or failed) ─────────────────────────
    now = datetime.utcnow()
    due_task = (
        db.query(ScheduledTask)
          .filter(
              ScheduledTask.student_id == student.id,
              ScheduledTask.completed_at.is_(None),
              ScheduledTask.due_at <= now,
          )
          .order_by(ScheduledTask.due_at)
          .first()
    )

    if due_task:
        q = due_task.question
        topic = db.query(Topic).filter(Topic.id == q.topic_id).first()
        return ExtensionContextOut(
            task_id=due_task.id,
            task_type=due_task.task_type.value,
            topic_name=topic.name if topic else "Unknown",
            question=QuestionOut.model_validate(q),
            rationale=(
                f"You have a due {due_task.task_type.value} task on this question "
                f"(was due {due_task.due_at.strftime('%b %d')})."
            ),
            mode="DUE_TASK",
        )

    # ── 3: Keyword-inferred topic ─────────────────────────────────────────────
    page_content = payload.page_text or payload.page_url
    inferred_topic = _infer_topic_keyword(page_content, db)
    if inferred_topic:
        q = _pick_unanswered(student.id, inferred_topic.id, db)
        if q:
            return ExtensionContextOut(
                task_id=None,
                task_type=None,
                topic_name=inferred_topic.name,
                question=QuestionOut.model_validate(q),
                rationale=(
                    f"This page seems to be about {inferred_topic.name}. "
                    "Testing your durable understanding now."
                ),
                mode="KEYWORD",
            )

    # ── 4: Random fallback ────────────────────────────────────────────────────
    q = _pick_any_question(student.id, db)
    if not q:
        raise HTTPException(status_code=404, detail="No questions available")

    topic = db.query(Topic).filter(Topic.id == q.topic_id).first()
    return ExtensionContextOut(
        task_id=None,
        task_type=None,
        topic_name=topic.name if topic else "Unknown",
        question=QuestionOut.model_validate(q),
        rationale="No specific topic detected — serving a random knowledge check.",
        mode="RANDOM",
    )


@router.post("/submit", response_model=ExtensionSubmitOut)
def submit_extension_attempt(
    payload: ExtensionSubmitRequest,
    x_api_key: str = Header(..., description="Student API key"),
    db: Session = Depends(get_db),
):
    """
    Record an attempt from the Chrome Extension and return immediate feedback.
    Supports LLM-based short-answer grading when USE_LLM_GRADING=true.
    """
    student = _get_student(x_api_key, db)

    question = db.query(Question).filter(Question.id == payload.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # ── Grading ───────────────────────────────────────────────────────────────
    llm_feedback: Optional[str] = None
    is_correct: bool

    use_llm_grading = (
        settings.USE_LLM_GRADING
        and settings.OPENAI_API_KEY
        and question.question_type == QuestionType.SHORT_TEXT
    )

    if use_llm_grading:
        from app.services.llm_service import grade_short_answer

        # For LLM-generated questions options holds the rubric; otherwise empty
        rubric = question.options if question.variant_template == "LLM_CONTEXT" else []

        grading = grade_short_answer(
            question_text=question.text,
            correct_answer=question.correct_answer,
            rubric=rubric or [],
            student_answer=payload.answer,
        )

        if grading is not None:
            is_correct = grading.score_0_1 >= 0.7
            llm_feedback = grading.feedback
        else:
            # LLM grading failed — fall back
            is_correct = _check_correctness_deterministic(question, payload.answer)
    else:
        is_correct = _check_correctness_deterministic(question, payload.answer)

    # ── Persist attempt ───────────────────────────────────────────────────────
    attempt = Attempt(
        student_id=student.id,
        question_id=question.id,
        answer=payload.answer,
        confidence=payload.confidence,
        reasoning=payload.reasoning,
        is_correct=is_correct,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # Mark specific task done
    if payload.task_id:
        task = (
            db.query(ScheduledTask)
              .filter(
                  ScheduledTask.id == payload.task_id,
                  ScheduledTask.student_id == student.id,
              )
              .first()
        )
        if task:
            task.completed_at = datetime.utcnow()
            db.commit()

    mark_completed_tasks(db, student.id, question.id)
    schedule_follow_ups(db)

    # ── Build feedback ────────────────────────────────────────────────────────
    if llm_feedback:
        # LLM provided a rich explanation
        feedback = "Correct!" if is_correct else "Not quite."
        explanation = llm_feedback
    elif is_correct:
        feedback = "Correct!"
        if payload.confidence >= 7:
            explanation = "Well calibrated — you were confident and right."
        else:
            explanation = "You got it right, but you seemed uncertain. Keep practising to build confidence."
    else:
        feedback = "Not quite."
        if payload.confidence >= 7:
            explanation = (
                f"Overconfidence detected — you were confident ({payload.confidence}/10) "
                f"but the answer was: \"{question.correct_answer}\". "
                "A RETEST has been scheduled to strengthen this."
            )
        else:
            explanation = (
                f"The correct answer is: \"{question.correct_answer}\". "
                "A follow-up question has been scheduled for spaced repetition."
            )

    # ── Recompute overall DUS ─────────────────────────────────────────────────
    updated_dus = _compute_overall_dus(db, student.id)

    return ExtensionSubmitOut(
        correct=is_correct,
        feedback=feedback,
        correct_answer=question.correct_answer,
        explanation=explanation,
        updated_dus=updated_dus,
    )
