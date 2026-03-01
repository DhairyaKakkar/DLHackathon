from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Student, UserRole


def get_student_by_api_key(
    x_api_key: str = Header(..., description="Student or Faculty API key"),
    db: Session = Depends(get_db),
) -> Student:
    student = db.query(Student).filter(Student.api_key == x_api_key).first()
    if not student:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return student


def require_faculty(
    current_user: Student = Depends(get_student_by_api_key),
) -> Student:
    if current_user.role != UserRole.FACULTY:
        raise HTTPException(status_code=403, detail="Faculty access required")
    return current_user
