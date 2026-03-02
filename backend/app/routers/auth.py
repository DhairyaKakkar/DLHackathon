"""
Auth endpoint — validate an API key and return the user's role.
Used by the frontend login page to authenticate students and faculty.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import Student, UserRole

router = APIRouter(prefix="/auth", tags=["Auth"])


class ValidateRequest(BaseModel):
    api_key: str


class ValidateResponse(BaseModel):
    role: str                   # "student" | "faculty"
    student_id: Optional[int]   # None for faculty
    name: str


@router.post("/validate", response_model=ValidateResponse)
def validate_api_key(payload: ValidateRequest, db: Session = Depends(get_db)):
    """
    Validate an API key. Returns role, student_id, and name.
    Returns 401 if the key is invalid.
    """
    student = db.query(Student).filter(Student.api_key == payload.api_key).first()
    if not student:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return ValidateResponse(
        role=student.role.value,
        student_id=student.id if student.role == UserRole.STUDENT else None,
        name=student.name,
    )
