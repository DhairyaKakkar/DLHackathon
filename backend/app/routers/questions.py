from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question, Topic
from app.schemas import QuestionCreate, QuestionOut, VariantGenerateRequest
from app.services.variant_generator import generate_variants

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.post("/", response_model=QuestionOut, status_code=201)
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)):
    if not db.query(Topic).filter(Topic.id == payload.topic_id).first():
        raise HTTPException(status_code=404, detail="Topic not found")
    q = Question(
        topic_id=payload.topic_id,
        text=payload.text,
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        correct_answer=payload.correct_answer,
        options=payload.options,
        is_variant=False,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.get("/", response_model=list[QuestionOut])
def list_questions(
    topic_id: int | None = Query(None),
    variants_only: bool = Query(False),
    originals_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    qs = db.query(Question)
    if topic_id is not None:
        qs = qs.filter(Question.topic_id == topic_id)
    if variants_only:
        qs = qs.filter(Question.is_variant == True)  # noqa: E712
    if originals_only:
        qs = qs.filter(Question.is_variant == False)  # noqa: E712
    return qs.all()


@router.get("/{question_id}", response_model=QuestionOut)
def get_question(question_id: int, db: Session = Depends(get_db)):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q


@router.post("/{question_id}/variants", response_model=list[QuestionOut], status_code=201)
def create_variants(
    question_id: int,
    payload: VariantGenerateRequest,
    db: Session = Depends(get_db),
):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    if q.is_variant:
        raise HTTPException(status_code=400, detail="Cannot generate variants of a variant")
    variants = generate_variants(db, q, payload.num_variants, payload.use_llm)
    return variants


@router.get("/{question_id}/variants", response_model=list[QuestionOut])
def list_variants(question_id: int, db: Session = Depends(get_db)):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return db.query(Question).filter(Question.original_question_id == question_id).all()
