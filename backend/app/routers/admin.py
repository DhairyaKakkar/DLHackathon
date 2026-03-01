from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.seed import reset_and_reseed, seed
from app.services.scheduler_service import schedule_follow_ups

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/seed", summary="Seed database with demo data (if not already seeded)")
def seed_db(db: Session = Depends(get_db)):
    seed(db)
    return {"status": "ok", "message": "Seed complete (skipped if already seeded)"}


@router.post("/reset", summary="⚠️ Reset database and reseed with fresh demo data")
def reset_db(db: Session = Depends(get_db)):
    reset_and_reseed(db)
    return {"status": "ok", "message": "Database reset and reseeded"}


@router.post("/scheduler/run", summary="Manually trigger the scheduler tick")
def run_scheduler(db: Session = Depends(get_db)):
    created = schedule_follow_ups(db)
    return {"status": "ok", "tasks_created": created}
