import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    ForeignKey, Text, JSON, Enum as SAEnum, Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class QuestionType(str, enum.Enum):
    MCQ = "MCQ"
    SHORT_TEXT = "SHORT_TEXT"


class TaskType(str, enum.Enum):
    RETEST = "RETEST"
    TRANSFER = "TRANSFER"


class UserRole(str, enum.Enum):
    STUDENT = "student"
    FACULTY = "faculty"


# ─── Models ───────────────────────────────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    api_key = Column(String(64), unique=True, nullable=False, index=True)
    role = Column(SAEnum(UserRole), default=UserRole.STUDENT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    attempts = relationship("Attempt", back_populates="student", lazy="dynamic")
    scheduled_tasks = relationship("ScheduledTask", back_populates="student", lazy="dynamic")
    class_schedules = relationship("ClassSchedule", back_populates="student", lazy="dynamic")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    questions = relationship("Question", back_populates="topic", lazy="dynamic")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    question_type = Column(SAEnum(QuestionType), nullable=False)
    difficulty = Column(Integer, default=3, nullable=False)       # 1–5
    correct_answer = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)                          # MCQ option list
    is_variant = Column(Boolean, default=False, nullable=False, index=True)
    original_question_id = Column(
        Integer, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    variant_template = Column(String(255), nullable=True)          # tag for generator used
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    topic = relationship("Topic", back_populates="questions")
    variants = relationship(
        "Question",
        primaryjoin="Question.id == remote(Question.original_question_id)",
        foreign_keys="[Question.original_question_id]",
        lazy="dynamic",
    )
    attempts = relationship("Attempt", back_populates="question", lazy="dynamic")
    scheduled_tasks = relationship("ScheduledTask", back_populates="question", lazy="dynamic")

    __table_args__ = (
        Index("ix_questions_topic_variant", "topic_id", "is_variant"),
    )


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    answer = Column(Text, nullable=False)
    confidence = Column(Integer, nullable=False)       # 1–10
    reasoning = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="attempts")
    question = relationship("Question", back_populates="attempts")

    __table_args__ = (
        Index("ix_attempts_student_question", "student_id", "question_id"),
        Index("ix_attempts_student_created", "student_id", "created_at"),
    )


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    due_at = Column(DateTime, nullable=False, index=True)
    task_type = Column(SAEnum(TaskType), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="scheduled_tasks")
    question = relationship("Question", back_populates="scheduled_tasks")

    __table_args__ = (
        Index("ix_tasks_student_due", "student_id", "due_at"),
    )


class ClassSchedule(Base):
    """A recurring class in a student's school timetable."""
    __tablename__ = "class_schedules"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_name = Column(String(255), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    days_of_week = Column(JSON, nullable=False)    # ["monday", "wednesday", "friday"]
    class_time = Column(String(5), nullable=False)  # "09:00" 24h
    teacher_name = Column(String(255), nullable=True)
    room = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="class_schedules")
    topic = relationship("Topic")
    pre_class_tasks = relationship("PreClassTask", back_populates="schedule", lazy="dynamic")


class PreClassTask(Base):
    """Generated pre-class brief or post-class check for a scheduled class."""
    __tablename__ = "pre_class_tasks"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule_id = Column(Integer, ForeignKey("class_schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    task_type = Column(String(20), nullable=False)  # PRE_CLASS_BRIEF | POST_CLASS_CHECK
    class_datetime = Column(DateTime, nullable=False)
    brief_data = Column(JSON, nullable=True)         # GPT-4o output, cached
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student")
    schedule = relationship("ClassSchedule", back_populates="pre_class_tasks")

    __table_args__ = (
        Index("ix_pre_class_tasks_student_dt", "student_id", "class_datetime"),
    )
