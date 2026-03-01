from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Attempt, Question, Student, QuestionType
from app.schemas import AttemptCreate, AttemptOut
from app.services.scheduler_service import mark_completed_tasks, schedule_follow_ups

router = APIRouter(prefix="/attempts", tags=["Attempts"])


def _check_correctness(question: Question, answer: str) -> bool:
    """
    MCQ: case-insensitive exact match after stripping whitespace.
    SHORT_TEXT: case-insensitive substring match (answer contains correct_answer keyword).
    """
    correct = question.correct_answer.strip().lower()
    given = answer.strip().lower()

    if question.question_type == QuestionType.MCQ:
        return given == correct

    # SHORT_TEXT: accept if the core keyword appears in the answer
    return correct in given or given in correct


@router.post("/", response_model=AttemptOut, status_code=201)
def submit_attempt(payload: AttemptCreate, db: Session = Depends(get_db)):
    if not db.query(Student).filter(Student.id == payload.student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")

    question = db.query(Question).filter(Question.id == payload.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct = _check_correctness(question, payload.answer)

    attempt = Attempt(
        student_id=payload.student_id,
        question_id=payload.question_id,
        answer=payload.answer,
        confidence=payload.confidence,
        reasoning=payload.reasoning,
        is_correct=is_correct,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # Mark any due tasks for this student+question as completed
    mark_completed_tasks(db, payload.student_id, payload.question_id)

    # Immediately create follow-up tasks based on this new attempt
    schedule_follow_ups(db)

    return attempt


@router.get("/", response_model=list[AttemptOut])
def list_attempts(
    student_id: int | None = Query(None),
    question_id: int | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(Attempt)
    if student_id is not None:
        q = q.filter(Attempt.student_id == student_id)
    if question_id is not None:
        q = q.filter(Attempt.question_id == question_id)
    return q.order_by(Attempt.created_at.desc()).limit(limit).all()


@router.get("/{attempt_id}", response_model=AttemptOut)
def get_attempt(attempt_id: int, db: Session = Depends(get_db)):
    a = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return a
