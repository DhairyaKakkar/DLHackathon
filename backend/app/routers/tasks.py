from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import ScheduledTask, Student, Question
from app.schemas import ScheduledTaskOut

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/student/{student_id}", response_model=list[ScheduledTaskOut])
def get_due_tasks(
    student_id: int,
    include_future: bool = Query(False, description="Include not-yet-due tasks"),
    db: Session = Depends(get_db),
):
    """
    Return due (or all) scheduled tasks for a student.
    Tasks are ordered by due_at ascending (most urgent first).
    """
    if not db.query(Student).filter(Student.id == student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")

    q = (
        db.query(ScheduledTask)
        .options(joinedload(ScheduledTask.question))
        .filter(
            ScheduledTask.student_id == student_id,
            ScheduledTask.completed_at == None,  # noqa: E711
        )
    )
    if not include_future:
        q = q.filter(ScheduledTask.due_at <= datetime.utcnow())

    return q.order_by(ScheduledTask.due_at).all()


@router.get("/", response_model=list[ScheduledTaskOut])
def list_all_tasks(
    due_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """List all scheduled tasks (admin/debug view)."""
    q = (
        db.query(ScheduledTask)
        .options(joinedload(ScheduledTask.question))
        .filter(ScheduledTask.completed_at == None)  # noqa: E711
    )
    if due_only:
        q = q.filter(ScheduledTask.due_at <= datetime.utcnow())
    return q.order_by(ScheduledTask.due_at).all()
