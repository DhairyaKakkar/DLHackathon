import secrets
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.schemas import StudentCreate, StudentOut

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/me", response_model=StudentOut)
def get_me(
    x_api_key: str = Header(..., description="Student API key"),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.api_key == x_api_key).first()
    if not student:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return student


@router.post("/", response_model=StudentOut, status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    if db.query(Student).filter(Student.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    student = Student(
        name=payload.name,
        email=payload.email,
        role=payload.role,
        api_key=secrets.token_hex(16),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/", response_model=list[StudentOut])
def list_students(db: Session = Depends(get_db)):
    return db.query(Student).all()


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db)):
    s = db.query(Student).filter(Student.id == student_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    return s
