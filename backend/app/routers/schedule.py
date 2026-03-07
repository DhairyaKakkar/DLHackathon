"""
Schedule management endpoints.

GET  /api/v1/schedule/student/{student_id}               — fetch schedule + readiness
POST /api/v1/schedule/student/{student_id}               — save/replace full schedule
POST /api/v1/schedule/student/{student_id}/parse-text    — GPT-4o parse freeform text
GET  /api/v1/schedule/student/{student_id}/brief/{id}    — get/generate pre-class brief
POST /api/v1/schedule/student/{student_id}/brief/{id}/complete — mark brief done
GET  /api/v1/schedule/student/{student_id}/post-class/{id} — post-class check
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClassSchedule, PreClassTask, Student, Topic
from app.services.metrics_service import compute_topic_metrics
from app.services.pre_class_service import (
    generate_post_class_check,
    generate_pre_class_brief,
    get_next_class_datetime,
    get_readiness_score,
    parse_schedule_from_text,
    parse_schedule_from_image,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedule", tags=["Schedule"])


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class ClassScheduleIn(BaseModel):
    subject_name: str
    topic_id: Optional[int] = None
    days_of_week: list[str]
    class_time: str
    teacher_name: Optional[str] = None
    room: Optional[str] = None


class ClassScheduleOut(BaseModel):
    id: int
    subject_name: str
    topic_id: Optional[int]
    topic_name: Optional[str]
    days_of_week: list[str]
    class_time: str
    teacher_name: Optional[str]
    room: Optional[str]
    next_class_datetime: Optional[str]
    days_until_next_class: Optional[int]
    hours_until_next_class: Optional[float]
    readiness_score: Optional[float]
    is_urgent: bool    # class within 24h
    is_upcoming: bool  # class within 7 days


class ParseTextIn(BaseModel):
    text: str


class ParseImageIn(BaseModel):
    image_b64: str   # base64-encoded image, no data-URI prefix
    media_type: str  # e.g. "image/jpeg", "image/png"


# ─── Helper ───────────────────────────────────────────────────────────────────

def _build_schedule_out(s: ClassSchedule, db: Session, student_id: int) -> ClassScheduleOut:
    next_dt = get_next_class_datetime(s.days_of_week, s.class_time)
    now = datetime.utcnow()
    hours_until = ((next_dt - now).total_seconds() / 3600) if next_dt else None
    days_until = int(hours_until // 24) if hours_until is not None else None

    topic_name = None
    readiness = None
    if s.topic_id:
        topic = db.query(Topic).filter(Topic.id == s.topic_id).first()
        topic_name = topic.name if topic else None
        try:
            metrics = compute_topic_metrics(db, student_id, s.topic_id)
            readiness = get_readiness_score(metrics.durable_understanding_score, days_until)
        except Exception:
            pass

    return ClassScheduleOut(
        id=s.id,
        subject_name=s.subject_name,
        topic_id=s.topic_id,
        topic_name=topic_name,
        days_of_week=s.days_of_week,
        class_time=s.class_time,
        teacher_name=s.teacher_name,
        room=s.room,
        next_class_datetime=next_dt.isoformat() if next_dt else None,
        days_until_next_class=days_until,
        hours_until_next_class=round(hours_until, 1) if hours_until is not None else None,
        readiness_score=readiness,
        is_urgent=(hours_until is not None and hours_until <= 24),
        is_upcoming=(days_until is not None and days_until <= 7),
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/student/{student_id}", response_model=list[ClassScheduleOut])
def get_student_schedule(student_id: int, db: Session = Depends(get_db)):
    schedules = (
        db.query(ClassSchedule)
        .filter(ClassSchedule.student_id == student_id)
        .all()
    )
    results = [_build_schedule_out(s, db, student_id) for s in schedules]
    # Sort by hours until next class (most urgent first)
    return sorted(results, key=lambda x: x.hours_until_next_class if x.hours_until_next_class is not None else 9999)


@router.post("/student/{student_id}", response_model=list[ClassScheduleOut])
def save_student_schedule(
    student_id: int,
    items: list[ClassScheduleIn],
    db: Session = Depends(get_db),
):
    # Verify student exists
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Replace entire schedule
    db.query(ClassSchedule).filter(ClassSchedule.student_id == student_id).delete()
    for item in items:
        entry = ClassSchedule(
            student_id=student_id,
            subject_name=item.subject_name,
            topic_id=item.topic_id,
            days_of_week=item.days_of_week,
            class_time=item.class_time,
            teacher_name=item.teacher_name,
            room=item.room,
        )
        db.add(entry)
    db.commit()

    return get_student_schedule(student_id=student_id, db=db)


@router.post("/student/{student_id}/parse-text", response_model=list[ClassScheduleIn])
def parse_schedule_text(
    student_id: int,
    body: ParseTextIn,
    db: Session = Depends(get_db),
):
    """GPT-4o parses a freeform schedule description into structured class entries."""
    topics = db.query(Topic).all()
    topic_names = [t.name for t in topics]
    parsed = parse_schedule_from_text(body.text, topic_names)
    if not parsed:
        raise HTTPException(status_code=422, detail="Could not parse schedule from text")
    return parsed


@router.post("/student/{student_id}/parse-image", response_model=list[ClassScheduleIn])
def parse_schedule_image(
    student_id: int,
    body: ParseImageIn,
    db: Session = Depends(get_db),
):
    """GPT-4o Vision extracts structured class info from a timetable photo."""
    topics = db.query(Topic).all()
    topic_names = [t.name for t in topics]
    parsed = parse_schedule_from_image(body.image_b64, body.media_type, topic_names)
    if not parsed:
        raise HTTPException(status_code=422, detail="Could not extract schedule from image")
    return parsed


@router.get("/student/{student_id}/brief/{schedule_id}")
def get_pre_class_brief(
    student_id: int,
    schedule_id: int,
    db: Session = Depends(get_db),
):
    """Get or generate (and cache) a personalized pre-class brief."""
    schedule = db.query(ClassSchedule).filter(
        ClassSchedule.id == schedule_id,
        ClassSchedule.student_id == student_id,
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule entry not found")

    # Return cached brief if generated today
    today = datetime.utcnow().date()
    existing = (
        db.query(PreClassTask)
        .filter(
            PreClassTask.student_id == student_id,
            PreClassTask.schedule_id == schedule_id,
            PreClassTask.task_type == "PRE_CLASS_BRIEF",
        )
        .order_by(PreClassTask.created_at.desc())
        .first()
    )
    if existing and existing.brief_data and existing.created_at.date() == today:
        return existing.brief_data

    # Generate new brief
    next_dt = get_next_class_datetime(schedule.days_of_week, schedule.class_time)
    now = datetime.utcnow()
    days_until = int(((next_dt - now).total_seconds() / 86400)) if next_dt else None

    topic_metrics = None
    if schedule.topic_id:
        try:
            topic_metrics = compute_topic_metrics(db, student_id, schedule.topic_id)
        except Exception:
            pass

    topics = db.query(Topic).all()
    topic_names = [t.name for t in topics]

    brief = generate_pre_class_brief(
        subject_name=schedule.subject_name,
        topic_metrics=topic_metrics,
        days_until=days_until,
        topic_names=topic_names,
    )
    if not brief:
        raise HTTPException(status_code=503, detail="Failed to generate brief — check OPENAI_API_KEY")

    # Cache it
    task = PreClassTask(
        student_id=student_id,
        schedule_id=schedule_id,
        task_type="PRE_CLASS_BRIEF",
        class_datetime=next_dt or now,
        brief_data=brief,
    )
    db.add(task)
    db.commit()
    return brief


@router.post("/student/{student_id}/brief/{schedule_id}/complete")
def complete_pre_class_brief(
    student_id: int,
    schedule_id: int,
    db: Session = Depends(get_db),
):
    """Mark the pre-class brief as completed."""
    task = (
        db.query(PreClassTask)
        .filter(
            PreClassTask.student_id == student_id,
            PreClassTask.schedule_id == schedule_id,
            PreClassTask.task_type == "PRE_CLASS_BRIEF",
            PreClassTask.completed_at == None,  # noqa: E711
        )
        .order_by(PreClassTask.created_at.desc())
        .first()
    )
    if task:
        task.completed_at = datetime.utcnow()
        db.commit()
    return {"ok": True}


@router.get("/student/{student_id}/post-class/{schedule_id}")
def get_post_class_check(
    student_id: int,
    schedule_id: int,
    db: Session = Depends(get_db),
):
    """Generate a post-class consolidation check."""
    schedule = db.query(ClassSchedule).filter(
        ClassSchedule.id == schedule_id,
        ClassSchedule.student_id == student_id,
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule entry not found")

    # Return cached post-class check if generated today
    today = datetime.utcnow().date()
    existing = (
        db.query(PreClassTask)
        .filter(
            PreClassTask.student_id == student_id,
            PreClassTask.schedule_id == schedule_id,
            PreClassTask.task_type == "POST_CLASS_CHECK",
        )
        .order_by(PreClassTask.created_at.desc())
        .first()
    )
    if existing and existing.brief_data and existing.created_at.date() == today:
        return existing.brief_data

    topic_metrics = None
    if schedule.topic_id:
        try:
            topic_metrics = compute_topic_metrics(db, student_id, schedule.topic_id)
        except Exception:
            pass

    check = generate_post_class_check(
        subject_name=schedule.subject_name,
        topic_metrics=topic_metrics,
    )
    if not check:
        raise HTTPException(status_code=503, detail="Failed to generate post-class check")

    task = PreClassTask(
        student_id=student_id,
        schedule_id=schedule_id,
        task_type="POST_CLASS_CHECK",
        class_datetime=datetime.utcnow(),
        brief_data=check,
    )
    db.add(task)
    db.commit()
    return check
