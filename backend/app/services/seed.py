"""
Seed the database with demo data that showcases EALE metrics:

  Alice Chen  — good mastery, poor transfer (memorises surface form)
  Bob Martinez — severely overconfident, low accuracy on DS + Algorithms
  Faculty Dana — faculty role for cohort dashboard

Timestamps are back-dated so the scheduler will mark retests as already-due.
"""
import secrets
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import Student, Topic, Question, Attempt, ScheduledTask, QuestionType, TaskType, UserRole
from app.database import SessionLocal

logger = logging.getLogger(__name__)

NOW = datetime.utcnow()


def _dt(days_ago: float, hours_ago: float = 0) -> datetime:
    return NOW - timedelta(days=days_ago, hours=hours_ago)


def _attempt(
    db: Session,
    student: Student,
    question: Question,
    answer: str,
    confidence: int,
    is_correct: bool,
    days_ago: float,
    reasoning: str = "",
) -> Attempt:
    a = Attempt(
        student_id=student.id,
        question_id=question.id,
        answer=answer,
        confidence=confidence,
        is_correct=is_correct,
        reasoning=reasoning,
        created_at=_dt(days_ago),
    )
    db.add(a)
    return a


def _task(
    db: Session,
    student: Student,
    question: Question,
    due_days_from_now: float,
    task_type: TaskType,
):
    t = ScheduledTask(
        student_id=student.id,
        question_id=question.id,
        due_at=NOW + timedelta(days=due_days_from_now),
        task_type=task_type,
        created_at=NOW,
    )
    db.add(t)
    return t


def is_seeded(db: Session) -> bool:
    return db.query(Student).count() > 0


def seed(db: Session) -> None:
    if is_seeded(db):
        logger.info("Database already seeded — skipping.")
        return

    logger.info("Seeding database …")

    # ── Students ──────────────────────────────────────────────────────────────
    alice = Student(
        name="Alice Chen",
        email="alice@example.com",
        api_key="student-alice-key",
        role=UserRole.STUDENT,
    )
    bob = Student(
        name="Bob Martinez",
        email="bob@example.com",
        api_key="student-bob-key",
        role=UserRole.STUDENT,
    )
    dana = Student(
        name="Dana Faculty",
        email="dana@example.com",
        api_key="faculty-dana-key",
        role=UserRole.FACULTY,
    )
    db.add_all([alice, bob, dana])
    db.flush()

    # ── Topics ────────────────────────────────────────────────────────────────
    t_py = Topic(name="Python Basics", description="Foundational Python syntax and types")
    t_ds = Topic(name="Data Structures", description="Lists, stacks, queues, and complexity")
    t_alg = Topic(name="Algorithms", description="Sorting and searching algorithms")
    db.add_all([t_py, t_ds, t_alg])
    db.flush()

    # ── Questions — Python Basics ──────────────────────────────────────────────
    q1 = Question(
        topic_id=t_py.id,
        text="What does `len([1, 2, 3])` return?",
        question_type=QuestionType.MCQ,
        difficulty=1,
        correct_answer="3",
        options=["1", "3", "0", "2"],
        is_variant=False,
    )
    q2 = Question(
        topic_id=t_py.id,
        text="Which keyword is used to define a function in Python?",
        question_type=QuestionType.MCQ,
        difficulty=1,
        correct_answer="def",
        options=["func", "def", "function", "define"],
        is_variant=False,
    )
    q3 = Question(
        topic_id=t_py.id,
        text="What type does Python assign to `3.14`?",
        question_type=QuestionType.MCQ,
        difficulty=2,
        correct_answer="float",
        options=["int", "float", "double", "str"],
        is_variant=False,
    )
    db.add_all([q1, q2, q3])
    db.flush()

    # Variants for Python Basics
    q1v1 = Question(
        topic_id=t_py.id,
        text="How many elements are in the tuple `('a', 'b', 'c', 'd')`?",
        question_type=QuestionType.MCQ,
        difficulty=1,
        correct_answer="4",
        options=["3", "4", "1", "5"],
        is_variant=True,
        original_question_id=q1.id,
        variant_template="number_substitution",
    )
    q1v2 = Question(
        topic_id=t_py.id,
        text="What is the output of `len({'x': 1, 'y': 2})`?",
        question_type=QuestionType.MCQ,
        difficulty=2,
        correct_answer="2",
        options=["1", "4", "2", "3"],
        is_variant=True,
        original_question_id=q1.id,
        variant_template="context_shift",
    )
    q2v1 = Question(
        topic_id=t_py.id,
        text="To create a reusable block of code in Python, you write: `___ my_func():`",
        question_type=QuestionType.SHORT_TEXT,
        difficulty=1,
        correct_answer="def",
        options=None,
        is_variant=True,
        original_question_id=q2.id,
        variant_template="rephrase",
    )
    q3v1 = Question(
        topic_id=t_py.id,
        text="Is the value `2.0` of type `int` in Python?",
        question_type=QuestionType.MCQ,
        difficulty=2,
        correct_answer="No, it is float",
        options=["Yes, it is int", "No, it is float", "Yes, all numbers are int", "It has no type"],
        is_variant=True,
        original_question_id=q3.id,
        variant_template="rephrase",
    )
    db.add_all([q1v1, q1v2, q2v1, q3v1])
    db.flush()

    # ── Questions — Data Structures ───────────────────────────────────────────
    q4 = Question(
        topic_id=t_ds.id,
        text="Which data structure follows LIFO (Last In, First Out)?",
        question_type=QuestionType.MCQ,
        difficulty=2,
        correct_answer="Stack",
        options=["Queue", "Stack", "Heap", "Array"],
        is_variant=False,
    )
    q5 = Question(
        topic_id=t_ds.id,
        text="What is the time complexity of accessing a Python list element by index?",
        question_type=QuestionType.MCQ,
        difficulty=3,
        correct_answer="O(1)",
        options=["O(n)", "O(1)", "O(log n)", "O(n²)"],
        is_variant=False,
    )
    q6 = Question(
        topic_id=t_ds.id,
        text="What is the key difference between a list and a tuple in Python?",
        question_type=QuestionType.SHORT_TEXT,
        difficulty=3,
        correct_answer="tuple",
        options=None,
        is_variant=False,
    )
    db.add_all([q4, q5, q6])
    db.flush()

    q4v1 = Question(
        topic_id=t_ds.id,
        text="A function call stack uses which data structure principle?",
        question_type=QuestionType.MCQ,
        difficulty=3,
        correct_answer="Stack (LIFO)",
        options=["Queue (FIFO)", "Stack (LIFO)", "Heap", "Graph"],
        is_variant=True,
        original_question_id=q4.id,
        variant_template="context_shift",
    )
    q5v1 = Question(
        topic_id=t_ds.id,
        text="If a list has 1 million elements, how long does it take to access element at index 500,000?",
        question_type=QuestionType.MCQ,
        difficulty=3,
        correct_answer="Constant time O(1)",
        options=["Linear time O(n)", "Constant time O(1)", "Logarithmic O(log n)", "Quadratic O(n²)"],
        is_variant=True,
        original_question_id=q5.id,
        variant_template="number_substitution",
    )
    db.add_all([q4v1, q5v1])
    db.flush()

    # ── Questions — Algorithms ────────────────────────────────────────────────
    q7 = Question(
        topic_id=t_alg.id,
        text="What is the time complexity of binary search?",
        question_type=QuestionType.MCQ,
        difficulty=3,
        correct_answer="O(log n)",
        options=["O(n)", "O(log n)", "O(n log n)", "O(1)"],
        is_variant=False,
    )
    q8 = Question(
        topic_id=t_alg.id,
        text="Which sorting algorithm guarantees O(n log n) in the worst case?",
        question_type=QuestionType.MCQ,
        difficulty=4,
        correct_answer="Merge Sort",
        options=["Bubble Sort", "Quick Sort", "Merge Sort", "Insertion Sort"],
        is_variant=False,
    )
    db.add_all([q7, q8])
    db.flush()

    q7v1 = Question(
        topic_id=t_alg.id,
        text="Binary search on 1024 sorted elements requires at most how many comparisons? (write the number)",
        question_type=QuestionType.SHORT_TEXT,
        difficulty=4,
        correct_answer="10",
        options=None,
        is_variant=True,
        original_question_id=q7.id,
        variant_template="number_substitution",
    )
    db.add_all([q7v1])
    db.flush()

    # ── Alice's Attempts ──────────────────────────────────────────────────────
    # Pattern: high mastery on originals, poor transfer on variants.
    # Python Basics
    _attempt(db, alice, q1, "3", 8, True, 9.0)           # baseline
    _attempt(db, alice, q1, "3", 9, True, 8.0)           # retest day 1
    _attempt(db, alice, q1, "3", 8, True, 6.0)           # retest day 3
    _attempt(db, alice, q1v1, "3", 8, False, 5.0,        # transfer FAIL
             "I thought it was the same as the original")
    _attempt(db, alice, q1v2, "1", 7, False, 5.0)        # transfer FAIL
    _attempt(db, alice, q2, "def", 7, True, 9.0)
    _attempt(db, alice, q2v1, "def", 6, True, 7.0)       # transfer OK (simple rephrase)
    _attempt(db, alice, q3, "float", 8, True, 9.0)
    _attempt(db, alice, q3v1, "Yes, it is int", 8, False, 7.0)  # transfer FAIL

    # Data Structures
    _attempt(db, alice, q4, "Stack", 7, True, 8.0)
    _attempt(db, alice, q4, "Stack", 8, True, 7.0)        # retest day 1
    _attempt(db, alice, q4, "Stack", 7, True, 5.0)        # retest day 3
    _attempt(db, alice, q4v1, "Queue (FIFO)", 7, False, 4.0)   # transfer FAIL
    _attempt(db, alice, q5, "O(1)", 6, True, 8.0)
    _attempt(db, alice, q5v1, "Linear time O(n)", 6, False, 6.0)  # transfer FAIL

    # Algorithms — retention drop at day 7
    _attempt(db, alice, q7, "O(log n)", 7, True, 11.0)   # baseline
    _attempt(db, alice, q7, "O(log n)", 7, True, 10.0)   # retest day 1 ✓
    _attempt(db, alice, q7, "O(n)", 6, False, 8.0)        # retest day 3 ✗ ← retention drop!
    _attempt(db, alice, q7v1, "8", 5, False, 7.0)         # transfer FAIL
    _attempt(db, alice, q8, "Merge Sort", 8, True, 11.0)

    # ── Bob's Attempts ────────────────────────────────────────────────────────
    # Pattern: overconfident — high confidence, low accuracy on DS + Alg.
    # Python Basics (mediocre but somewhat right)
    _attempt(db, bob, q1, "3", 7, True, 6.0)
    _attempt(db, bob, q2, "def", 7, True, 6.0)
    _attempt(db, bob, q3, "int", 8, False, 6.0,           # wrong, overconfident
             "I think integers cover all numbers")

    # Data Structures — overconfident and mostly wrong
    _attempt(db, bob, q4, "Queue", 9, False, 5.0,         # WRONG, conf=9
             "I always mix these up but I'm sure it's queue")
    _attempt(db, bob, q4v1, "Queue (FIFO)", 8, False, 4.0)  # transfer: still wrong
    _attempt(db, bob, q5, "O(n)", 9, False, 5.0)           # WRONG, conf=9
    _attempt(db, bob, q5v1, "Linear time O(n)", 8, False, 4.0)
    _attempt(db, bob, q6, "lists are mutable", 8, True, 5.0)  # correct (partial match)

    # Algorithms — very overconfident, completely wrong
    _attempt(db, bob, q7, "O(n)", 9, False, 6.0)           # WRONG conf=9
    _attempt(db, bob, q7, "O(n log n)", 8, False, 5.0)     # retest: STILL wrong
    _attempt(db, bob, q7v1, "100", 8, False, 4.0)          # transfer: wrong
    _attempt(db, bob, q8, "Quick Sort", 9, False, 6.0)     # WRONG conf=9

    db.flush()

    # ── Scheduled Tasks (some already due for demo) ───────────────────────────
    # Alice — next retests due now
    _task(db, alice, q7, -0.1, TaskType.RETEST)    # overdue
    _task(db, alice, q4, 1.0, TaskType.RETEST)     # due tomorrow
    _task(db, alice, q4v1, -0.1, TaskType.TRANSFER)  # overdue transfer

    # Bob — overdue retests
    _task(db, bob, q4, -0.1, TaskType.RETEST)      # overdue
    _task(db, bob, q7, -0.1, TaskType.RETEST)      # overdue
    _task(db, bob, q4v1, -0.1, TaskType.TRANSFER)  # overdue transfer
    _task(db, bob, q5v1, 1.0, TaskType.TRANSFER)   # due tomorrow

    db.commit()
    logger.info("Seeding complete.")


def reset_and_reseed(db: Session) -> None:
    """Drop all data and reseed. Use with caution."""
    from app.models import Base
    from app.database import engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed(db)


def run_seed():
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
