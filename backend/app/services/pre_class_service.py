"""
Pre-class brief and schedule intelligence service.

Provides:
  - get_next_class_datetime()       — next real-calendar occurrence of a recurring class
  - get_readiness_score()           — urgency-weighted DUS
  - parse_schedule_from_text()      — GPT-4o parses natural language schedule
  - parse_schedule_from_image()     — GPT-4o Vision parses timetable photo
  - generate_pre_class_brief()      — GPT-4o personalized prep packet + quiz questions
  - generate_post_class_check()     — GPT-4o post-class knowledge check questions
  - extract_content_from_pdf()      — PyMuPDF renders every slide page → GPT-4o reads all
  - extract_content_text()          — GPT-4o Vision extracts text from uploaded content image
  - generate_lesson_from_content()  — GPT-4o teaches key concepts from uploaded lecture content
  - generate_pre_lecture_quiz()     — GPT-4o generates assessment from lecture content
"""

import base64
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from app.config import settings

logger = logging.getLogger(__name__)

DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class ParsedClass(BaseModel):
    subject_name: str
    topic_id: Optional[int] = None
    days_of_week: list[str]
    class_time: str          # "09:00"
    teacher_name: Optional[str] = None
    room: Optional[str] = None


class PrepQuestion(BaseModel):
    id: int
    question: str
    type: str                 # "MCQ" | "SHORT_TEXT"
    options: Optional[list[str]] = None
    correct: str
    explanation: str


class PreClassBrief(BaseModel):
    readiness_score: float    # 0–100, urgency-weighted
    summary: str
    focus_areas: list[str]
    quick_review_points: list[str]
    prep_questions: list[PrepQuestion]
    estimated_prep_time: str
    personalized_tip: str


class PostClassCheck(BaseModel):
    summary: str
    check_questions: list[PrepQuestion]
    reflection_prompts: list[str]


# ─── Utilities ────────────────────────────────────────────────────────────────

def get_next_class_datetime(days_of_week: list[str], class_time: str) -> Optional[datetime]:
    """Return the next calendar datetime for a recurring class (within next 14 days)."""
    try:
        hour, minute = map(int, class_time.split(":"))
    except Exception:
        return None

    target_weekdays = [DAY_MAP[d.lower()] for d in days_of_week if d.lower() in DAY_MAP]
    if not target_weekdays:
        return None

    now = datetime.utcnow()
    for delta in range(15):
        candidate = now + timedelta(days=delta)
        if candidate.weekday() in target_weekdays:
            candidate_dt = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate_dt > now:
                return candidate_dt
    return None


def get_readiness_score(dus: float, days_until: Optional[int]) -> float:
    """
    Urgency-weighted readiness: penalizes low DUS when class is near.
    Formula: readiness = DUS * urgency_factor
      - 0 days: factor 0.70 (must act now)
      - 1 day:  factor 0.85
      - 2 days: factor 0.92
      - 3+ days: factor 1.0 (no urgency penalty)
    """
    if days_until is None:
        return round(dus, 1)
    factors = {0: 0.70, 1: 0.85, 2: 0.92}
    factor = factors.get(days_until, 1.0)
    return round(min(100.0, dus * factor), 1)


def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=settings.OPENAI_API_KEY)


# ─── GPT-4o: parse schedule from text ────────────────────────────────────────

_PARSE_SYSTEM = """\
You are a school schedule parser. Extract structured class information from the student's description or timetable image.
Map each class to the closest topic from the provided list (topic_id = null if no match).

Days must be lowercase: monday, tuesday, wednesday, thursday, friday, saturday, sunday
Time must be 24h format: "09:00", "14:30"

Return ONLY valid JSON:
{
  "classes": [
    {
      "subject_name": "Physics",
      "topic_id": null,
      "days_of_week": ["monday", "wednesday"],
      "class_time": "09:00",
      "teacher_name": "Mr. Smith",
      "room": "Lab 3"
    }
  ]
}
"""


def parse_schedule_from_text(text: str, topic_names: list[str]) -> Optional[list[dict]]:
    """Use GPT-4o to parse a freeform schedule description into structured data."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _PARSE_SYSTEM},
                {"role": "user", "content": (
                    f"Available EALE topics: {', '.join(topic_names)}\n\n"
                    f"Student's schedule description:\n{text}"
                )},
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
            temperature=0.1,
        )
        data = __import__("json").loads(resp.choices[0].message.content)
        return data.get("classes", [])
    except Exception as exc:
        logger.warning("[PreClass] parse_schedule failed: %s", exc)
        return None


def parse_schedule_from_image(image_b64: str, media_type: str, topic_names: list[str]) -> Optional[list[dict]]:
    """
    Use GPT-4o Vision to extract structured schedule data from a timetable photo.
    image_b64: base64-encoded image (no data-URI prefix).
    media_type: e.g. "image/jpeg", "image/png", "image/webp"
    """
    if not settings.OPENAI_API_KEY:
        return None
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _PARSE_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Available EALE topics: {', '.join(topic_names)}\n\n"
                                "Extract every class from this timetable image. "
                                "Return all classes you can identify with their days and times."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.1,
        )
        data = __import__("json").loads(resp.choices[0].message.content)
        return data.get("classes", [])
    except Exception as exc:
        logger.warning("[PreClass] parse_schedule_from_image failed: %s", exc)
        return None


# ─── GPT-4o: pre-class brief ─────────────────────────────────────────────────

_BRIEF_SYSTEM = """\
You are an expert educational coach generating a personalized pre-class preparation brief.
The student's performance data is provided. Generate a targeted prep packet using gpt-4o.

Return ONLY valid JSON:
{
  "readiness_score": <float 0-100>,
  "summary": "<2-3 sentence assessment of readiness and what to focus on>",
  "focus_areas": ["<specific subtopic 1>", "<specific subtopic 2>", "<specific subtopic 3>"],
  "quick_review_points": [
    "<key fact or formula to remember>",
    "<key fact or formula to remember>",
    "<key fact or formula to remember>",
    "<key fact or formula to remember>"
  ],
  "prep_questions": [
    {
      "id": 1,
      "question": "<question text>",
      "type": "MCQ",
      "options": ["A", "B", "C", "D"],
      "correct": "<exact option text>",
      "explanation": "<why this is correct>"
    },
    ... (5 questions total, mix of MCQ and SHORT_TEXT)
  ],
  "estimated_prep_time": "<e.g. 40 minutes>",
  "personalized_tip": "<one specific tip based on their weakest metric>"
}

For SHORT_TEXT questions, omit "options" and set "correct" to a model answer.
"""


def generate_pre_class_brief(
    subject_name: str,
    topic_metrics: Any,          # TopicMetrics dataclass or None
    days_until: Optional[int],
    topic_names: list[str],
) -> Optional[dict]:
    """Call GPT-4o to generate a personalized pre-class brief."""
    if not settings.OPENAI_API_KEY:
        return None

    # Build context from metrics if available
    metrics_block = ""
    if topic_metrics:
        metrics_block = (
            f"\nStudent performance on this topic:\n"
            f"  DUS (Durable Understanding Score): {topic_metrics.durable_understanding_score:.1f}/100\n"
            f"  Mastery: {topic_metrics.mastery:.1f}/100\n"
            f"  Retention: {topic_metrics.retention:.1f}/100\n"
            f"  Transfer: {topic_metrics.transfer_robustness:.1f}/100\n"
            f"  Calibration: {topic_metrics.calibration:.1f}/100\n"
            f"  Overconfidence gap: {topic_metrics.overconfidence_gap:+.1f} points\n"
            f"  Total attempts: {topic_metrics.total_attempts}\n"
            f"  Mastery insight: {topic_metrics.mastery_explanation}\n"
            f"  Retention insight: {topic_metrics.retention_explanation}\n"
            f"  Transfer insight: {topic_metrics.transfer_explanation}\n"
            f"  Calibration insight: {topic_metrics.calibration_explanation}\n"
        )
    else:
        metrics_block = "\nNo prior performance data available for this subject yet."

    days_str = f"{days_until} day{'s' if days_until != 1 else ''}" if days_until is not None else "soon"

    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _BRIEF_SYSTEM},
                {"role": "user", "content": (
                    f"Subject: {subject_name}\n"
                    f"Class is in: {days_str}\n"
                    f"{metrics_block}\n"
                    f"Available EALE topics for reference: {', '.join(topic_names)}\n\n"
                    "Generate a highly personalized pre-class prep brief. "
                    "Make the questions exactly calibrated to the student's current level — "
                    "not too easy, not too hard. Focus on their specific weak areas."
                )},
            ],
            response_format={"type": "json_object"},
            max_tokens=2500,
            temperature=0.4,
        )
        brief = __import__("json").loads(resp.choices[0].message.content)
        # Override readiness_score with our formula if we have DUS
        if topic_metrics and days_until is not None:
            brief["readiness_score"] = get_readiness_score(
                topic_metrics.durable_understanding_score, days_until
            )
        return brief
    except Exception as exc:
        logger.warning("[PreClass] generate_pre_class_brief failed: %s", exc)
        return None


# ─── GPT-4o: post-class check ────────────────────────────────────────────────

_POST_SYSTEM = """\
You are an expert educational coach generating a post-class knowledge consolidation check.
The student just finished a class. Generate questions to lock in what they just learned.

Return ONLY valid JSON:
{
  "summary": "<encouraging 2-sentence message about consolidating learning>",
  "check_questions": [
    {
      "id": 1,
      "question": "<question on content covered in class>",
      "type": "MCQ",
      "options": ["A", "B", "C", "D"],
      "correct": "<exact option>",
      "explanation": "<explanation>"
    },
    ... (5 questions)
  ],
  "reflection_prompts": [
    "<open-ended reflection question about the class>",
    "<open-ended reflection question>",
    "<open-ended reflection question>"
  ]
}
"""


def generate_post_class_check(
    subject_name: str,
    topic_metrics: Any,
) -> Optional[dict]:
    """Call GPT-4o to generate post-class consolidation questions."""
    if not settings.OPENAI_API_KEY:
        return None

    metrics_block = ""
    if topic_metrics:
        metrics_block = (
            f"\nCurrent metrics after the class:\n"
            f"  DUS: {topic_metrics.durable_understanding_score:.1f}/100\n"
            f"  Weakest area: retention ({topic_metrics.retention:.1f}/100)\n"
        )

    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _POST_SYSTEM},
                {"role": "user", "content": (
                    f"Subject just completed: {subject_name}\n"
                    f"{metrics_block}\n"
                    "Generate consolidation questions to lock in what was just learned."
                )},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.4,
        )
        return __import__("json").loads(resp.choices[0].message.content)
    except Exception as exc:
        logger.warning("[PreClass] generate_post_class_check failed: %s", exc)
        return None


# ─── PDF: render all pages → GPT-4o reads every slide ────────────────────────

MAX_PDF_PAGES = 40  # cap for very long decks


def extract_content_from_pdf(pdf_b64: str) -> Optional[str]:
    """
    Convert every page of a PDF (lecture slides) to a PNG image using PyMuPDF,
    then send all pages to GPT-4o vision in a single call for comprehensive extraction.
    Also includes raw text layer as additional context.
    """
    if not settings.OPENAI_API_KEY:
        return None
    try:
        import fitz  # pymupdf

        pdf_bytes = base64.b64decode(pdf_b64)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = min(len(doc), MAX_PDF_PAGES)

        # Extract raw text from all pages (cheap, fast)
        raw_text_parts = []
        for i in range(total_pages):
            page_text = doc[i].get_text("text").strip()
            if page_text:
                raw_text_parts.append(f"[Slide {i + 1}]\n{page_text}")
        raw_text = "\n\n".join(raw_text_parts)

        # Render each page as PNG → base64
        page_images_content = []
        for i in range(total_pages):
            page = doc[i]
            # 150 DPI gives clear text without being enormous
            mat = fitz.Matrix(150 / 72, 150 / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            png_b64 = base64.b64encode(png_bytes).decode()
            page_images_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{png_b64}",
                    "detail": "high",
                },
            })

        doc.close()

        # Build message: system prompt text + all slide images
        content: list[dict] = [
            {
                "type": "text",
                "text": (
                    f"These are {total_pages} slides from a lecture PDF. "
                    "Read EVERY slide carefully and extract ALL content: "
                    "headings, bullet points, definitions, formulas, diagrams (describe them), "
                    "code snippets, tables, and any annotations. "
                    "Preserve slide structure with [Slide N] markers. "
                    "Be exhaustive — this will be used to teach a student the lecture content.\n\n"
                    f"Raw text layer (may be incomplete for image-heavy slides):\n{raw_text[:4000]}"
                ),
            },
            *page_images_content,
        ]

        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=8000,
            temperature=0.1,
        )
        return resp.choices[0].message.content.strip()

    except Exception as exc:
        logger.warning("[PreClass] extract_content_from_pdf failed: %s", exc)
        return None


# ─── GPT-4o: extract text from uploaded content image ────────────────────────

def extract_content_text(image_b64: str, media_type: str) -> Optional[str]:
    """
    Use GPT-4o Vision to extract all readable text + structure from an uploaded
    lecture slide, whiteboard photo, or handwritten notes image.
    """
    if not settings.OPENAI_API_KEY:
        return None
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "This is an image of lecture slides, notes, or a whiteboard. "
                                "Extract ALL text, headings, bullet points, formulas, and diagrams descriptions "
                                "in full detail. Preserve the structure as much as possible. "
                                "Output plain text — no JSON, no markdown fencing."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=3000,
            temperature=0.1,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("[PreClass] extract_content_text failed: %s", exc)
        return None


# ─── GPT-4o: generate lesson from uploaded lecture content ───────────────────

_LESSON_FROM_CONTENT_SYSTEM = """\
You are an expert university tutor. A student has shared the content that will be covered in
their upcoming lecture. Your job is to teach them the key concepts BEFORE the class so they
can participate confidently and absorb more during the lecture.

Return ONLY valid JSON:
{
  "title": "<Lesson title, e.g. 'Pre-lecture: Binary Search Trees'>",
  "overview": "<2-3 sentence overview of what this lecture covers and why it matters>",
  "key_concepts": [
    {
      "name": "<Concept name>",
      "explanation": "<Clear, concise explanation (3-5 sentences)>",
      "example": "<A concrete, specific example that makes it click>",
      "common_mistake": "<The most common misconception students have about this>"
    }
  ],
  "quick_facts": [
    "<Key formula, definition, or rule to memorise>",
    "<Key formula, definition, or rule to memorise>",
    "<Key formula, definition, or rule to memorise>",
    "<Key formula, definition, or rule to memorise>"
  ],
  "lecture_tip": "<One specific tip for getting the most out of the upcoming lecture>",
  "estimated_time": "<e.g. 20 minutes>"
}

Include 3-6 key_concepts. Be concrete and pedagogically sound.
"""


def generate_lesson_from_content(content_text: str, subject_name: str) -> Optional[dict]:
    """GPT-4o generates a structured pre-lecture lesson from uploaded content."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _LESSON_FROM_CONTENT_SYSTEM},
                {"role": "user", "content": (
                    f"Subject: {subject_name}\n\n"
                    f"Lecture content uploaded by student:\n{content_text[:8000]}\n\n"
                    "Teach me the key concepts from this lecture content so I'm prepared for class."
                )},
            ],
            response_format={"type": "json_object"},
            max_tokens=3000,
            temperature=0.4,
        )
        return __import__("json").loads(resp.choices[0].message.content)
    except Exception as exc:
        logger.warning("[PreClass] generate_lesson_from_content failed: %s", exc)
        return None


# ─── GPT-4o: pre-lecture assessment from uploaded content ────────────────────

_PRE_LECTURE_QUIZ_SYSTEM = """\
You are an expert assessment designer. Based on the lecture content provided, generate
5-7 diagnostic questions that test whether the student understands the prerequisite knowledge
AND can engage with the new material. Mix foundational checks with anticipatory questions.

Return ONLY valid JSON:
{
  "questions": [
    {
      "id": 1,
      "question": "<question text>",
      "type": "MCQ",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct": "<exact option text>",
      "explanation": "<why this is correct, and what it connects to in the lecture>"
    },
    {
      "id": 2,
      "question": "<question text>",
      "type": "SHORT_TEXT",
      "correct": "<model answer>",
      "explanation": "<explanation>"
    }
  ],
  "passing_score": 70,
  "diagnostic_note": "<1-sentence note on what a low score means vs a high score for this lecture>"
}

For SHORT_TEXT questions, omit "options". Mix MCQ and SHORT_TEXT. Calibrate to the lecture level.
"""


def generate_pre_lecture_quiz(content_text: str, subject_name: str) -> Optional[dict]:
    """GPT-4o generates a pre-lecture self-assessment from uploaded content."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _PRE_LECTURE_QUIZ_SYSTEM},
                {"role": "user", "content": (
                    f"Subject: {subject_name}\n\n"
                    f"Lecture content:\n{content_text[:8000]}\n\n"
                    "Generate a pre-lecture diagnostic assessment for this content."
                )},
            ],
            response_format={"type": "json_object"},
            max_tokens=2500,
            temperature=0.4,
        )
        return __import__("json").loads(resp.choices[0].message.content)
    except Exception as exc:
        logger.warning("[PreClass] generate_pre_lecture_quiz failed: %s", exc)
        return None
