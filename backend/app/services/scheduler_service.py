"""
Spaced-repetition scheduler.

Runs on a background thread (APScheduler BackgroundScheduler).
Every tick it:
  1. Finds attempts that don't yet have follow-up RETEST tasks for all intervals.
  2. Creates the missing ScheduledTask rows.
  3. (Optional) Creates TRANSFER tasks for original-question attempts
     that have available variants.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Attempt, ScheduledTask, TaskType, Question

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


# ─── Core scheduling logic ────────────────────────────────────────────────────

def schedule_follow_ups(db: Session) -> int:
    """
    For every original-question attempt that lacks follow-up tasks,
    create RETEST tasks at each configured interval.
    Returns number of tasks created.
    """
    intervals: list[int] = settings.RETEST_INTERVALS_DAYS
    created_count = 0

    # Find all attempts on non-variant questions
    orig_attempts = (
        db.query(Attempt)
        .join(Question, Attempt.question_id == Question.id)
        .filter(Question.is_variant == False)  # noqa: E712
        .all()
    )

    for attempt in orig_attempts:
        for days in intervals:
            due_at = attempt.created_at + timedelta(days=days)

            # Skip if already past the useful window (> 30 days in future from now)
            if due_at > datetime.utcnow() + timedelta(days=30):
                continue

            # Check if this exact (student, question, due_day, RETEST) task exists
            exists = (
                db.query(ScheduledTask)
                .filter(
                    ScheduledTask.student_id == attempt.student_id,
                    ScheduledTask.question_id == attempt.question_id,
                    ScheduledTask.task_type == TaskType.RETEST,
                    # same day bucket
                    func.date(ScheduledTask.due_at) == due_at.date(),
                )
                .first()
            )
            if not exists:
                task = ScheduledTask(
                    student_id=attempt.student_id,
                    question_id=attempt.question_id,
                    due_at=due_at,
                    task_type=TaskType.RETEST,
                )
                db.add(task)
                created_count += 1

    # TRANSFER tasks: for each attempt on an original question with variants,
    # schedule a TRANSFER task shortly after the second interval
    variant_map: dict[int, list[int]] = {}  # orig_id → [variant_ids]

    def _get_variants(orig_id: int) -> list[int]:
        if orig_id not in variant_map:
            rows = (
                db.query(Question.id)
                .filter(Question.original_question_id == orig_id)
                .all()
            )
            variant_map[orig_id] = [r[0] for r in rows]
        return variant_map[orig_id]

    for attempt in orig_attempts:
        variant_ids = _get_variants(attempt.question_id)
        for vid in variant_ids:
            due_at = attempt.created_at + timedelta(days=2)
            if due_at > datetime.utcnow() + timedelta(days=30):
                continue
            exists = (
                db.query(ScheduledTask)
                .filter(
                    ScheduledTask.student_id == attempt.student_id,
                    ScheduledTask.question_id == vid,
                    ScheduledTask.task_type == TaskType.TRANSFER,
                    func.date(ScheduledTask.due_at) == due_at.date(),
                )
                .first()
            )
            if not exists:
                task = ScheduledTask(
                    student_id=attempt.student_id,
                    question_id=vid,
                    due_at=due_at,
                    task_type=TaskType.TRANSFER,
                )
                db.add(task)
                created_count += 1

    if created_count:
        db.commit()
        logger.info("Scheduler created %d new tasks", created_count)

    return created_count


def mark_completed_tasks(db: Session, student_id: int, question_id: int) -> None:
    """Mark any pending tasks for this student+question as completed."""
    now = datetime.utcnow()
    db.query(ScheduledTask).filter(
        ScheduledTask.student_id == student_id,
        ScheduledTask.question_id == question_id,
        ScheduledTask.completed_at == None,  # noqa: E711
        ScheduledTask.due_at <= now,
    ).update({"completed_at": now}, synchronize_session=False)
    db.commit()


# ─── APScheduler wiring ───────────────────────────────────────────────────────

def _run_scheduler_tick():
    db: Session = SessionLocal()
    try:
        schedule_follow_ups(db)
    except Exception:
        logger.exception("Error in scheduler tick")
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    interval = settings.SCHEDULER_INTERVAL_SECONDS
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_scheduler_tick,
        "interval",
        seconds=interval,
        id="follow_up_scheduler",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started (interval=%ds)", interval)


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
