"""
Core metric computations for EALE.

Durable Understanding Score (DUS) formula:
    DUS = 0.30 × mastery + 0.30 × retention + 0.25 × transfer + 0.15 × calibration

All component scores are on [0, 100].
"""
from collections import defaultdict
from typing import Any
from sqlalchemy.orm import Session

from app.models import Question, Attempt


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _accuracy(attempts: list) -> float:
    if not attempts:
        return 0.0
    return sum(1 for a in attempts if a.is_correct) / len(attempts)


# ─── Mastery ──────────────────────────────────────────────────────────────────

def compute_mastery(original_attempts: list) -> tuple[float, str]:
    """Recent accuracy on original (non-variant) questions."""
    recent = original_attempts[-10:] if len(original_attempts) > 10 else original_attempts

    if not recent:
        return 50.0, "No original-question attempts found; defaulting to neutral score."

    acc = _accuracy(recent)
    score = round(acc * 100, 2)

    if score >= 80:
        explanation = (
            f"Mastery is strong: {score:.0f}% accuracy across {len(recent)} recent attempts."
        )
    elif score >= 60:
        explanation = (
            f"Mastery is moderate: {score:.0f}% accuracy across {len(recent)} recent attempts."
        )
    else:
        explanation = (
            f"Mastery is weak: only {score:.0f}% accuracy across {len(recent)} recent attempts."
        )
    return score, explanation


# ─── Retention ────────────────────────────────────────────────────────────────

def compute_retention(original_attempts: list) -> tuple[float, dict[str, float], str]:
    """
    Bin attempts by time gap from first attempt on each question.
    Returns (score, bin_accuracy_pct_dict, explanation).
    """
    if not original_attempts:
        return 50.0, {}, "No attempts found; retention score defaults to neutral."

    by_question: dict[int, list] = defaultdict(list)
    for a in original_attempts:
        by_question[a.question_id].append(a)

    bins: dict[str, list[bool]] = defaultdict(list)

    for q_id, q_attempts in by_question.items():
        q_attempts_sorted = sorted(q_attempts, key=lambda a: a.created_at)
        first_time = q_attempts_sorted[0].created_at

        for attempt in q_attempts_sorted:
            gap_h = (attempt.created_at - first_time).total_seconds() / 3600
            if gap_h < 24:
                bins["same_day"].append(attempt.is_correct)
            elif gap_h < 72:
                bins["day_1_3"].append(attempt.is_correct)
            elif gap_h < 168:
                bins["day_3_7"].append(attempt.is_correct)
            else:
                bins["week_plus"].append(attempt.is_correct)

    bin_order = ["same_day", "day_1_3", "day_3_7", "week_plus"]
    bin_accuracy: dict[str, float] = {}
    for b in bin_order:
        if bins[b]:
            bin_accuracy[b] = sum(bins[b]) / len(bins[b])

    bin_accuracy_pct = {k: round(v * 100, 1) for k, v in bin_accuracy.items()}

    if len(bin_accuracy) < 2:
        score = bin_accuracy.get("same_day", 0.5) * 100
        explanation = (
            "Not enough data across different time gaps to compute a full retention curve; "
            f"using baseline accuracy of {score:.0f}%."
        )
        return round(score, 2), bin_accuracy_pct, explanation

    baseline_keys = ["same_day", "day_1_3"]
    later_keys = ["day_3_7", "week_plus"]

    baseline_vals = [bin_accuracy[k] for k in baseline_keys if k in bin_accuracy]
    later_vals = [bin_accuracy[k] for k in later_keys if k in bin_accuracy]

    baseline_acc = sum(baseline_vals) / len(baseline_vals) if baseline_vals else 0.5
    later_acc = sum(later_vals) / len(later_vals) if later_vals else baseline_acc

    drop = max(0.0, baseline_acc - later_acc)
    # Penalise drops: a 33% drop → score of 50; 67% drop → score of 0
    score = max(0.0, min(100.0, 100.0 * (1.0 - drop * 1.5)))

    baseline_pct = round(baseline_acc * 100)
    later_pct = round(later_acc * 100)

    if drop > 0.30:
        explanation = (
            f"Retention is low: accuracy drops from {baseline_pct}% (early attempts) "
            f"to {later_pct}% after extended gaps — significant forgetting detected."
        )
    elif drop > 0.10:
        explanation = (
            f"Retention is moderate: accuracy drops from {baseline_pct}% to {later_pct}% "
            "over time, suggesting some forgetting."
        )
    else:
        explanation = (
            f"Retention is strong: accuracy stays near {later_pct}% "
            "even after extended time gaps."
        )

    return round(score, 2), bin_accuracy_pct, explanation


# ─── Transfer ─────────────────────────────────────────────────────────────────

def compute_transfer(
    original_attempts: list, variant_attempts: list
) -> tuple[float, str]:
    """Compare variant accuracy vs original accuracy."""
    if not variant_attempts:
        return 50.0, (
            "No variant attempts found; transfer score defaults to neutral (insufficient data)."
        )

    orig_acc = _accuracy(original_attempts)
    var_acc = _accuracy(variant_attempts)

    if not original_attempts:
        score = round(var_acc * 100, 2)
        return score, f"Only variant attempts available; transfer score is {score:.0f}%."

    transfer_ratio = var_acc / max(orig_acc, 0.01)
    score = min(100.0, max(0.0, transfer_ratio * 100.0))

    orig_pct = round(orig_acc * 100)
    var_pct = round(var_acc * 100)

    if score >= 90:
        explanation = (
            f"Transfer is excellent: {var_pct}% accuracy on variants vs {orig_pct}% "
            "on originals — knowledge generalises well."
        )
    elif score >= 70:
        explanation = (
            f"Transfer is moderate: {var_pct}% on variants vs {orig_pct}% on originals — "
            "some generalisation gap."
        )
    else:
        explanation = (
            f"Transfer is poor: only {var_pct}% on variants vs {orig_pct}% on originals — "
            "student may have memorised surface form rather than the underlying concept."
        )

    return round(score, 2), explanation


# ─── Calibration ──────────────────────────────────────────────────────────────

def compute_calibration(
    all_attempts: list,
) -> tuple[float, float, str, list[dict[str, Any]]]:
    """
    ECE-like calibration score.
    Bins: 1-2, 3-4, 5-6, 7-8, 9-10.
    Returns (calibration_score, overconfidence_gap_pp, explanation, bin_details).
    """
    if not all_attempts:
        return 50.0, 0.0, "No attempts found; calibration defaults to neutral.", []

    BINS = [(1, 2, "1-2"), (3, 4, "3-4"), (5, 6, "5-6"), (7, 8, "7-8"), (9, 10, "9-10")]
    bin_details: list[dict[str, Any]] = []
    total = len(all_attempts)
    ece = 0.0

    for low, high, label in BINS:
        grp = [a for a in all_attempts if low <= a.confidence <= high]
        if not grp:
            continue
        mean_conf_norm = sum(a.confidence for a in grp) / len(grp) / 10.0
        acc = sum(1 for a in grp if a.is_correct) / len(grp)
        weight = len(grp) / total
        error = abs(mean_conf_norm - acc)
        ece += weight * error
        bin_details.append(
            {
                "bin": label,
                "count": len(grp),
                "mean_confidence": round(mean_conf_norm * 100, 1),
                "accuracy": round(acc * 100, 1),
                "error": round(error * 100, 1),
            }
        )

    calibration_score = max(0.0, min(100.0, 100.0 * (1.0 - ece)))

    mean_conf_all = sum(a.confidence for a in all_attempts) / len(all_attempts) / 10.0
    mean_acc_all = _accuracy(all_attempts)
    overconfidence_gap = round((mean_conf_all - mean_acc_all) * 100, 2)

    conf_pct = round(mean_conf_all * 100)
    acc_pct = round(mean_acc_all * 100)

    if overconfidence_gap > 15:
        explanation = (
            f"Significantly overconfident: average confidence is {conf_pct}% "
            f"but accuracy is only {acc_pct}% (gap: {overconfidence_gap:.0f}pp). "
            "Student consistently overestimates their understanding."
        )
    elif overconfidence_gap > 5:
        explanation = (
            f"Slightly overconfident: average confidence {conf_pct}% "
            f"vs accuracy {acc_pct}% (gap: {overconfidence_gap:.0f}pp)."
        )
    elif overconfidence_gap < -15:
        explanation = (
            f"Underconfident: accuracy is {acc_pct}% but confidence is only {conf_pct}% "
            f"(gap: {abs(overconfidence_gap):.0f}pp). Student underestimates their knowledge."
        )
    else:
        explanation = (
            f"Well calibrated: confidence ({conf_pct}%) closely matches accuracy ({acc_pct}%)."
        )

    return round(calibration_score, 2), overconfidence_gap, explanation, bin_details


# ─── Composite ────────────────────────────────────────────────────────────────

def compute_topic_metrics(
    topic_id: int,
    topic_name: str,
    original_q_ids: set[int],
    variant_q_ids: set[int],
    attempts: list,
) -> dict[str, Any]:
    """Compute full metric bundle for one student × topic."""
    orig_attempts = [a for a in attempts if a.question_id in original_q_ids]
    var_attempts = [a for a in attempts if a.question_id in variant_q_ids]

    mastery, mastery_exp = compute_mastery(orig_attempts)
    retention, retention_bins, retention_exp = compute_retention(orig_attempts)
    transfer, transfer_exp = compute_transfer(orig_attempts, var_attempts)
    calibration, overconf_gap, calib_exp, calib_bins = compute_calibration(attempts)

    dus = round(0.30 * mastery + 0.30 * retention + 0.25 * transfer + 0.15 * calibration, 2)

    if dus >= 80:
        dus_exp = (
            f"DUS of {dus:.0f} indicates durable understanding: "
            "high mastery, good retention, and reliable knowledge transfer."
        )
    elif dus >= 60:
        weak = min(
            [("mastery", mastery), ("retention", retention), ("transfer", transfer)],
            key=lambda x: x[1],
        )
        dus_exp = (
            f"DUS of {dus:.0f} indicates partial durability. "
            f"Weakest area: {weak[0]} ({weak[1]:.0f}/100). More practice recommended."
        )
    else:
        dus_exp = (
            f"DUS of {dus:.0f} indicates fragile mastery. "
            "Student needs more spaced practice and transfer exercises."
        )

    return {
        "topic_id": topic_id,
        "topic_name": topic_name,
        "total_attempts": len(attempts),
        "original_attempts": len(orig_attempts),
        "variant_attempts": len(var_attempts),
        "mastery": mastery,
        "mastery_explanation": mastery_exp,
        "retention": retention,
        "retention_bins": retention_bins,
        "retention_explanation": retention_exp,
        "transfer_robustness": transfer,
        "transfer_explanation": transfer_exp,
        "calibration": calibration,
        "overconfidence_gap": overconf_gap,
        "calibration_explanation": calib_exp,
        "calibration_bins": calib_bins,
        "durable_understanding_score": dus,
        "dus_formula": "DUS = 0.30 × mastery + 0.30 × retention + 0.25 × transfer + 0.15 × calibration",
        "dus_explanation": dus_exp,
    }


def load_student_topic_metrics(db: Session, student_id: int) -> list[dict[str, Any]]:
    """Load all topics and compute metrics for a student."""
    from app.models import Topic

    topics = db.query(Topic).all()
    results = []

    for topic in topics:
        q_all = db.query(Question).filter(Question.topic_id == topic.id).all()
        orig_ids = {q.id for q in q_all if not q.is_variant}
        var_ids = {q.id for q in q_all if q.is_variant}
        all_ids = orig_ids | var_ids

        if not all_ids:
            continue

        attempts = (
            db.query(Attempt)
            .filter(Attempt.student_id == student_id, Attempt.question_id.in_(all_ids))
            .order_by(Attempt.created_at)
            .all()
        )

        metrics = compute_topic_metrics(topic.id, topic.name, orig_ids, var_ids, attempts)
        results.append(metrics)

    return results
