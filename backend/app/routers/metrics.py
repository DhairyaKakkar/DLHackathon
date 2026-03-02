from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import Student, Topic, Question, Attempt
from app.schemas import StudentDashboard, TopicMetrics, FacultyDashboard, FacultyTopicSummary, HistogramBucket
from app.services.metrics_service import load_student_topic_metrics, compute_topic_metrics

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/student/{student_id}", response_model=StudentDashboard)
def student_dashboard(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    topic_metrics = load_student_topic_metrics(db, student_id)

    if topic_metrics:
        overall_dus = round(
            sum(m["durable_understanding_score"] for m in topic_metrics) / len(topic_metrics), 2
        )
        if overall_dus >= 75:
            overall_exp = f"Overall DUS of {overall_dus:.0f} — strong durable understanding across topics."
        elif overall_dus >= 50:
            weak = min(topic_metrics, key=lambda m: m["durable_understanding_score"])
            overall_exp = (
                f"Overall DUS of {overall_dus:.0f} — partial durability. "
                f"Weakest topic: {weak['topic_name']} ({weak['durable_understanding_score']:.0f})."
            )
        else:
            overall_exp = (
                f"Overall DUS of {overall_dus:.0f} — learning appears fragile. "
                "Spaced practice and transfer exercises are recommended."
            )
    else:
        overall_dus = 0.0
        overall_exp = "No attempt data found."

    return StudentDashboard(
        student_id=student.id,
        student_name=student.name,
        topics=[TopicMetrics(**m) for m in topic_metrics],
        overall_dus=overall_dus,
        overall_explanation=overall_exp,
    )


@router.get("/student/{student_id}/topic/{topic_id}", response_model=TopicMetrics)
def topic_metrics_for_student(
    student_id: int, topic_id: int, db: Session = Depends(get_db)
):
    if not db.query(Student).filter(Student.id == student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    q_all = db.query(Question).filter(Question.topic_id == topic_id).all()
    orig_ids = {q.id for q in q_all if not q.is_variant}
    var_ids = {q.id for q in q_all if q.is_variant}
    all_ids = orig_ids | var_ids

    attempts = (
        db.query(Attempt)
        .filter(Attempt.student_id == student_id, Attempt.question_id.in_(all_ids))
        .order_by(Attempt.created_at)
        .all()
    )
    metrics = compute_topic_metrics(topic_id, topic.name, orig_ids, var_ids, attempts)
    return TopicMetrics(**metrics)


class ResourceOut(BaseModel):
    title: str
    url: str
    type: str
    description: str

class StudyStepOut(BaseModel):
    number: int
    title: str
    description: str
    duration: str

class TopicRoadmapOut(BaseModel):
    topic_name: str
    diagnosis: str
    steps: list[StudyStepOut]
    resources: list[ResourceOut]
    concepts: list[str]
    estimated_weeks: int


@router.get("/student/{student_id}/topic/{topic_id}/roadmap", response_model=TopicRoadmapOut)
def topic_roadmap(student_id: int, topic_id: int, db: Session = Depends(get_db)):
    """Generate a GPT-4o personalised improvement roadmap for one topic."""
    from app.services.llm_service import generate_topic_roadmap

    if not db.query(Student).filter(Student.id == student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    q_all = db.query(Question).filter(Question.topic_id == topic_id).all()
    orig_ids = {q.id for q in q_all if not q.is_variant}
    var_ids = {q.id for q in q_all if q.is_variant}
    all_ids = orig_ids | var_ids

    attempts = (
        db.query(Attempt)
        .filter(Attempt.student_id == student_id, Attempt.question_id.in_(all_ids))
        .order_by(Attempt.created_at)
        .all()
    )
    metrics = compute_topic_metrics(topic_id, topic.name, orig_ids, var_ids, attempts)

    result = generate_topic_roadmap(
        topic_name=topic.name,
        mastery=metrics["mastery"],
        retention=metrics["retention"],
        transfer=metrics["transfer_robustness"],
        calibration=metrics["calibration"],
        dus=metrics["durable_understanding_score"],
    )

    if result is None:
        raise HTTPException(status_code=503, detail="Roadmap generation unavailable — check OPENAI_API_KEY")

    return TopicRoadmapOut(
        topic_name=topic.name,
        diagnosis=result.diagnosis,
        steps=[StudyStepOut(**s.model_dump()) for s in result.steps],
        resources=[ResourceOut(**r.model_dump()) for r in result.resources],
        concepts=result.concepts,
        estimated_weeks=result.estimated_weeks,
    )


@router.get("/faculty", response_model=FacultyDashboard)
def faculty_dashboard(db: Session = Depends(get_db)):
    """Cohort-level aggregates for faculty view."""
    students = db.query(Student).filter(Student.role == "student").all()
    topics = db.query(Topic).all()

    num_students = len(students)
    topic_summaries: list[FacultyTopicSummary] = []

    all_dus_values: list[float] = []
    low_retention_topics: list[str] = []
    transfer_failure_topics: list[str] = []
    overconfidence_hotspots: list[str] = []
    ai_risk_student_set: set[str] = set()

    for topic in topics:
        q_all = db.query(Question).filter(Question.topic_id == topic.id).all()
        orig_ids = {q.id for q in q_all if not q.is_variant}
        var_ids = {q.id for q in q_all if q.is_variant}
        all_ids = orig_ids | var_ids

        if not all_ids:
            continue

        masteries, retentions, transfers, calibrations, dus_vals, overconf_gaps = [], [], [], [], [], []
        ai_dep_scores = []
        student_count = 0

        for student in students:
            attempts = (
                db.query(Attempt)
                .filter(Attempt.student_id == student.id, Attempt.question_id.in_(all_ids))
                .order_by(Attempt.created_at)
                .all()
            )
            if not attempts:
                continue
            m = compute_topic_metrics(topic.id, topic.name, orig_ids, var_ids, attempts)
            if m.get("ai_dependency_flagged"):
                ai_risk_student_set.add(student.name)
            masteries.append(m["mastery"])
            retentions.append(m["retention"])
            transfers.append(m["transfer_robustness"])
            calibrations.append(m["calibration"])
            dus_vals.append(m["durable_understanding_score"])
            overconf_gaps.append(m["overconfidence_gap"])
            ai_dep_scores.append(m.get("ai_dependency_score", 0.0))
            all_dus_values.append(m["durable_understanding_score"])
            student_count += 1

        if not student_count:
            continue

        def _avg(lst):
            return round(sum(lst) / len(lst), 2) if lst else 0.0

        avg_ret = _avg(retentions)
        avg_trans = _avg(transfers)
        avg_overconf = _avg(overconf_gaps)
        avg_ai_dep = _avg(ai_dep_scores)

        low_ret = avg_ret < 60
        trans_fail = avg_trans < 60
        overconf = avg_overconf > 15
        ai_dep_flag = avg_ai_dep >= 40

        if low_ret:
            low_retention_topics.append(topic.name)
        if trans_fail:
            transfer_failure_topics.append(topic.name)
        if overconf:
            overconfidence_hotspots.append(topic.name)

        topic_summaries.append(
            FacultyTopicSummary(
                topic_id=topic.id,
                topic_name=topic.name,
                num_students=student_count,
                avg_mastery=_avg(masteries),
                avg_retention=avg_ret,
                avg_transfer=avg_trans,
                avg_calibration=_avg(calibrations),
                avg_dus=_avg(dus_vals),
                avg_overconfidence_gap=avg_overconf,
                low_retention_flag=low_ret,
                transfer_failure_flag=trans_fail,
                overconfidence_flag=overconf,
                ai_dependency_flag=ai_dep_flag,
                avg_ai_dependency_score=avg_ai_dep,
            )
        )

    # DUS histogram (buckets: 0-20, 20-40, 40-60, 60-80, 80-100)
    bucket_ranges = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
    dus_distribution: list[HistogramBucket] = []
    for lo, hi in bucket_ranges:
        in_bucket = [v for v in all_dus_values if lo <= v < hi or (hi == 100 and v == 100)]
        dus_distribution.append(
            HistogramBucket(
                label=f"{lo}-{hi}",
                count=len(in_bucket),
                avg_value=round(sum(in_bucket) / len(in_bucket), 1) if in_bucket else 0.0,
            )
        )

    explanation_parts = []
    if low_retention_topics:
        explanation_parts.append(f"Low retention: {', '.join(low_retention_topics)}.")
    if transfer_failure_topics:
        explanation_parts.append(f"Transfer failures: {', '.join(transfer_failure_topics)}.")
    if overconfidence_hotspots:
        explanation_parts.append(f"Overconfidence hotspots: {', '.join(overconfidence_hotspots)}.")
    explanation = " | ".join(explanation_parts) or "No major issues detected across cohort."

    return FacultyDashboard(
        num_students=num_students,
        num_topics=len(topic_summaries),
        topic_summaries=topic_summaries,
        low_retention_topics=low_retention_topics,
        transfer_failure_topics=transfer_failure_topics,
        overconfidence_hotspots=overconfidence_hotspots,
        ai_risk_students=list(ai_risk_student_set),
        dus_distribution=dus_distribution,
        explanation=explanation,
    )
