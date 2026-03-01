from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models import QuestionType, TaskType, UserRole


# ─── Student ──────────────────────────────────────────────────────────────────

class StudentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    role: UserRole = UserRole.STUDENT


class StudentOut(BaseModel):
    id: int
    name: str
    email: str
    api_key: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Topic ────────────────────────────────────────────────────────────────────

class TopicCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TopicOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Question ─────────────────────────────────────────────────────────────────

class QuestionCreate(BaseModel):
    topic_id: int
    text: str = Field(..., min_length=1)
    question_type: QuestionType
    difficulty: int = Field(3, ge=1, le=5)
    correct_answer: str = Field(..., min_length=1)
    options: Optional[list[str]] = None   # required for MCQ

    @field_validator("options")
    @classmethod
    def validate_options(cls, v, info):
        qt = info.data.get("question_type")
        if qt == QuestionType.MCQ and (v is None or len(v) < 2):
            raise ValueError("MCQ questions require at least 2 options")
        return v


class QuestionOut(BaseModel):
    id: int
    topic_id: int
    text: str
    question_type: QuestionType
    difficulty: int
    correct_answer: str
    options: Optional[list[str]]
    is_variant: bool
    original_question_id: Optional[int]
    variant_template: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class VariantGenerateRequest(BaseModel):
    num_variants: int = Field(2, ge=1, le=5)
    use_llm: bool = False


# ─── Attempt ──────────────────────────────────────────────────────────────────

class AttemptCreate(BaseModel):
    student_id: int
    question_id: int
    answer: str = Field(..., min_length=1)
    confidence: int = Field(..., ge=1, le=10)
    reasoning: Optional[str] = Field(None, max_length=1000)


class AttemptOut(BaseModel):
    id: int
    student_id: int
    question_id: int
    answer: str
    confidence: int
    reasoning: Optional[str]
    is_correct: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Scheduled Task ───────────────────────────────────────────────────────────

class ScheduledTaskOut(BaseModel):
    id: int
    student_id: int
    question_id: int
    due_at: datetime
    task_type: TaskType
    completed_at: Optional[datetime]
    created_at: datetime
    question: QuestionOut

    model_config = {"from_attributes": True}


# ─── Metrics ──────────────────────────────────────────────────────────────────

class RetentionBin(BaseModel):
    bin: str
    accuracy_pct: float


class CalibrationBin(BaseModel):
    bin: str
    count: int
    mean_confidence: float
    accuracy: float
    error: float


class TopicMetrics(BaseModel):
    topic_id: int
    topic_name: str
    total_attempts: int
    original_attempts: int
    variant_attempts: int

    mastery: float
    mastery_explanation: str

    retention: float
    retention_bins: dict[str, float]
    retention_explanation: str

    transfer_robustness: float
    transfer_explanation: str

    calibration: float
    overconfidence_gap: float
    calibration_explanation: str
    calibration_bins: list[dict[str, Any]]

    durable_understanding_score: float
    dus_formula: str
    dus_explanation: str


class StudentDashboard(BaseModel):
    student_id: int
    student_name: str
    topics: list[TopicMetrics]
    overall_dus: float
    overall_explanation: str


class HistogramBucket(BaseModel):
    label: str
    count: int
    avg_value: float


class FacultyTopicSummary(BaseModel):
    topic_id: int
    topic_name: str
    num_students: int
    avg_mastery: float
    avg_retention: float
    avg_transfer: float
    avg_calibration: float
    avg_dus: float
    avg_overconfidence_gap: float
    low_retention_flag: bool
    transfer_failure_flag: bool
    overconfidence_flag: bool


class FacultyDashboard(BaseModel):
    num_students: int
    num_topics: int
    topic_summaries: list[FacultyTopicSummary]
    low_retention_topics: list[str]
    transfer_failure_topics: list[str]
    overconfidence_hotspots: list[str]
    dus_distribution: list[HistogramBucket]
    explanation: str
