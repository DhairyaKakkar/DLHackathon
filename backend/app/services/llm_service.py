"""
LLM utilities for the EALE Chrome Extension.

Provides two capabilities, both behind feature flags:

  infer_topic_and_generate_question(url, title, text_snippet)
      → Optional[LLMQuestion]   (None = use deterministic fallback)

  grade_short_answer(question_text, correct_answer, rubric, student_answer)
      → Optional[LLMGrading]   (None = use deterministic fallback)

Safety guarantees:
  - All LLM responses validated by strict Pydantic schemas.
  - Any failure (network, schema mismatch, timeout) returns None silently.
  - Page text capped at 2 000 chars; raw snippet never stored.
  - Cache key is SHA-256 of (url-without-query + title + snippet[:100]).
  - Rate limit: max 1 LLM generation per student per 60 s.
"""

import hashlib
import logging
import time
from typing import Literal, Optional

from pydantic import BaseModel, ValidationError, field_validator

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Pydantic schemas for strict LLM output validation ────────────────────────

class LLMQuestion(BaseModel):
    topic_name: str
    difficulty: int                          # 1–5
    question_type: Literal["MCQ", "SHORT_TEXT"]
    question_text: str
    options: Optional[list[str]] = None      # MCQ only
    correct_option: Optional[str] = None     # MCQ only (exact string from options)
    rubric: Optional[list[str]] = None       # SHORT_TEXT: key criteria
    rationale: str

    @field_validator("difficulty")
    @classmethod
    def clamp_difficulty(cls, v: int) -> int:
        return max(1, min(5, v))

    @field_validator("topic_name", "question_text", "rationale")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


class LLMGrading(BaseModel):
    correct: bool
    score_0_1: float                         # 0.0–1.0; ≥ 0.7 counts as correct
    feedback: str
    matched_criteria: list[str] = []

    @field_validator("score_0_1")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class LLMDifficultyAssessment(BaseModel):
    difficulty_score: int
    reasoning: str

    @field_validator("difficulty_score")
    @classmethod
    def clamp_difficulty(cls, v: int) -> int:
        return max(1, min(5, v))


# ─── In-memory TTL cache (question generation only) ───────────────────────────
# Maps cache_key -> (expiry_unix_ts, LLMQuestion)
_question_cache: dict[str, tuple[float, LLMQuestion]] = {}

# ─── Per-student rate limiter ─────────────────────────────────────────────────
# Maps student_id -> monotonic time of last LLM generation call
_rate_limit_log: dict[int, float] = {}
_RATE_LIMIT_SECONDS = 60


def is_rate_limited(student_id: int) -> bool:
    last = _rate_limit_log.get(student_id, 0.0)
    return (time.monotonic() - last) < _RATE_LIMIT_SECONDS


def record_llm_call(student_id: int) -> None:
    _rate_limit_log[student_id] = time.monotonic()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _cache_key(url: str, title: str, snippet: str) -> str:
    base = f"{url.split('?')[0].rstrip('/')}|{title.strip().lower()}|{snippet[:100]}"
    return hashlib.sha256(base.encode()).hexdigest()


def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=settings.OPENAI_API_KEY)


# ─── Prompts ──────────────────────────────────────────────────────────────────

_QUESTION_SYSTEM = """\
You are an expert educator generating transfer-style assessment questions.
Given a page excerpt, produce ONE question that tests deep conceptual understanding — NOT surface recall.
Prefer SHORT_TEXT for nuanced reasoning; use MCQ for clear-cut factual knowledge.

Return ONLY a valid JSON object with this exact schema (no markdown fences, no extra keys):
{
  "topic_name": "<concise academic subject, e.g. Macroeconomics>",
  "difficulty": <integer 1-5>,
  "question_type": "MCQ" | "SHORT_TEXT",
  "question_text": "<the question>",
  "options": ["option A", "option B", "option C", "option D"] | null,
  "correct_option": "<exact string from options>" | null,
  "rubric": ["<key criterion 1>", "<key criterion 2>", "<key criterion 3>"] | null,
  "rationale": "<one sentence: why this question tests transfer, not recall>"
}

Rules:
- MCQ: populate options (2–4 items) and correct_option; set rubric to null.
- SHORT_TEXT: populate rubric (2–4 key criteria a complete answer must cover); set options and correct_option to null.
- question_text must test understanding of the concept, not quote the page directly.
- topic_name must be a recognisable academic subject.
"""

_DIFFICULTY_SYSTEM = """\
You are analyzing a video lecture frame to assess how conceptually challenging the content is.
Examine any text, equations, diagrams, code, graphs, or visual content in the frame.

Return ONLY a valid JSON object:
{
  "difficulty_score": <integer 1-5>,
  "reasoning": "<one sentence>"
}

Score guide:
1 = Very easy / introductory / review
2 = Beginner-level, familiar concepts
3 = Moderate — some new ideas
4 = Challenging — dense notation, abstract concepts, multiple interconnected ideas
5 = Very difficult — complex derivations, heavy math, advanced theory
"""

_CONTEXT_HINT_MESSAGES: dict[str, str] = {
    "REWIND":           "The student just rewound the video — they likely missed or misunderstood something. Focus the question on the specific concept visible in the frame.",
    "MANUAL_PAUSE":     "The student paused the video, possibly to reflect. Ask a question that checks understanding of what was just explained.",
    "DIFFICULTY":       "This is a conceptually dense moment in the video. Ask a question that tests deep understanding of this specific concept.",
    "ATTENTION_RETURN": "The student was distracted and just returned. Quiz them on key concepts from this point in the video.",
}

_GRADING_SYSTEM = """\
You are a strict academic grader. Evaluate the student's answer against the question and rubric.
Apply rubric criteria literally — do not invent credit not clearly earned.

Return ONLY a valid JSON object:
{
  "correct": true | false,
  "score_0_1": <float 0.0–1.0>,
  "feedback": "<1–2 sentences: what was correct and/or what was missing>",
  "matched_criteria": ["<rubric criterion met>"]
}

Threshold: score >= 0.7 is treated as correct.
"""

_PROVE_IT_SYSTEM = """\
You are an academic integrity assistant. A student may have copy-pasted an answer.
Generate a short follow-up question to verify they genuinely understand what they submitted.

Rules:
- Ask them to explain ONE specific concept from their answer in their own words
- Make it impossible to answer without understanding the underlying idea
- Keep it one sentence ending with a question mark
- Do NOT repeat the original question

Return ONLY the follow-up question text. No JSON. No preamble.
"""


# ─── Public API ───────────────────────────────────────────────────────────────

def infer_topic_and_generate_question(
    url: str,
    title: str,
    text_snippet: str,
    screenshot_b64: Optional[str] = None,
    context_hint: Optional[str] = None,
) -> Optional[LLMQuestion]:
    """
    Call OpenAI to infer topic and produce a transfer-style question.
    Returns None on any failure — caller must fall back to deterministic logic.
    """
    if not settings.OPENAI_API_KEY:
        return None

    snippet = text_snippet[:2000]
    key = _cache_key(url, title, snippet)

    # Cache hit
    if key in _question_cache:
        expiry, cached = _question_cache[key]
        if time.time() < expiry:
            logger.info("[LLM] Cache hit (key=%.12s…)", key)
            return cached
        del _question_cache[key]

    hint_line = ""
    if context_hint and context_hint in _CONTEXT_HINT_MESSAGES:
        hint_line = f"\n\nContext: {_CONTEXT_HINT_MESSAGES[context_hint]}"

    user_text = (
        f"Page URL: {url}\n"
        f"Page title: {title}\n\n"
        f"Content excerpt:\n{snippet}\n\n"
        f"Generate a transfer-style question for this content.{hint_line}"
    )

    if screenshot_b64:
        user_content = [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{screenshot_b64}",
                "detail": "low",
            }},
        ]
    else:
        user_content = user_text  # string — unchanged path

    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _QUESTION_SYSTEM},
                {"role": "user",   "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=512,
            temperature=0.4,
        )
        raw = resp.choices[0].message.content
        result = LLMQuestion.model_validate_json(raw)

        # Store (only the derived question, never the raw snippet)
        _question_cache[key] = (time.time() + settings.LLM_CACHE_TTL_SECONDS, result)

        logger.info(
            "[LLM] Generated: topic=%r type=%s difficulty=%d",
            result.topic_name, result.question_type, result.difficulty,
        )
        return result

    except ValidationError as exc:
        logger.warning("[LLM] Question schema invalid: %s", exc)
        return None
    except Exception as exc:
        logger.warning("[LLM] Question generation failed (%s): %s", type(exc).__name__, exc)
        return None


def grade_short_answer(
    question_text: str,
    correct_answer: str,
    rubric: list[str],
    student_answer: str,
) -> Optional[LLMGrading]:
    """
    Call OpenAI to grade a short-text answer.
    Returns None on any failure — caller falls back to substring match.
    """
    if not settings.OPENAI_API_KEY:
        return None

    rubric_lines = "\n".join(f"- {r}" for r in rubric) if rubric else f"- {correct_answer}"

    user_msg = (
        f"Question: {question_text}\n\n"
        f"Rubric / key criteria:\n{rubric_lines}\n\n"
        f"Primary correct answer: {correct_answer}\n\n"
        f"Student answer: {student_answer}\n\n"
        "Grade this answer."
    )

    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _GRADING_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            response_format={"type": "json_object"},
            max_tokens=256,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content
        result = LLMGrading.model_validate_json(raw)

        logger.info(
            "[LLM] Graded: correct=%s score=%.2f",
            result.correct, result.score_0_1,
        )
        return result

    except ValidationError as exc:
        logger.warning("[LLM] Grading schema invalid: %s", exc)
        return None
    except Exception as exc:
        logger.warning("[LLM] Grading failed (%s): %s", type(exc).__name__, exc)
        return None


def grade_handwritten_answer(
    question_text: str,
    correct_answer: str,
    rubric: list[str],
    image_b64: str,
) -> Optional[LLMGrading]:
    """
    Use GPT-4 Vision to OCR and grade a handwritten answer in one call.
    Returns None on any failure — caller falls back to deterministic logic.
    """
    if not settings.OPENAI_API_KEY:
        return None

    rubric_lines = "\n".join(f"- {r}" for r in rubric) if rubric else f"- {correct_answer}"

    user_content = [
        {"type": "text", "text": (
            f"Question: {question_text}\n\n"
            f"Rubric / key criteria:\n{rubric_lines}\n\n"
            f"Correct answer: {correct_answer}\n\n"
            "The student submitted a handwritten answer (see image). "
            "Read the handwriting carefully and grade it against the rubric."
        )},
        {"type": "image_url", "image_url": {
            "url": f"data:image/jpeg;base64,{image_b64}",
            "detail": "high",
        }},
    ]

    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _GRADING_SYSTEM},
                {"role": "user",   "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=256,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content
        result = LLMGrading.model_validate_json(raw)

        logger.info(
            "[LLM] Handwriting graded: correct=%s score=%.2f",
            result.correct, result.score_0_1,
        )
        return result

    except ValidationError as exc:
        logger.warning("[LLM] Handwriting grading schema invalid: %s", exc)
        return None
    except Exception as exc:
        logger.warning("[LLM] Handwriting grading failed: %s", exc)
        return None


def assess_video_difficulty(
    frame_b64: str,
    caption_text: str = "",
) -> Optional[int]:
    """
    Assess how conceptually dense a video frame is. Returns 1–5 score, or None on failure.
    Called every 3 min passively; only triggers a quiz when score >= 4.
    """
    if not settings.OPENAI_API_KEY:
        return None

    user_content: list = [
        {"type": "image_url", "image_url": {
            "url": f"data:image/jpeg;base64,{frame_b64}",
            "detail": "low",   # fast + cheap — we just need overall density
        }},
    ]
    if caption_text:
        user_content.insert(0, {
            "type": "text",
            "text": f"Current captions / transcript:\n{caption_text[:500]}\n\nAssess the conceptual difficulty of this video frame.",
        })
    else:
        user_content.insert(0, {
            "type": "text",
            "text": "Assess the conceptual difficulty of this video frame.",
        })

    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _DIFFICULTY_SYSTEM},
                {"role": "user",   "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=128,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content
        result = LLMDifficultyAssessment.model_validate_json(raw)

        logger.info("[LLM] Video difficulty: score=%d (%s)", result.difficulty_score, result.reasoning)
        return result.difficulty_score

    except ValidationError as exc:
        logger.warning("[LLM] Video difficulty schema invalid: %s", exc)
        return None
    except Exception as exc:
        logger.warning("[LLM] Video difficulty assessment failed: %s", exc)
        return None


def generate_prove_it_question(
    question_text: str,
    student_answer: str,
    correct_answer: str,
) -> Optional[str]:
    """Generate a follow-up 'Prove It' question when paste is detected."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _PROVE_IT_SYSTEM},
                {"role": "user", "content": (
                    f"Original question: {question_text}\n"
                    f"Student's answer: {student_answer}\n"
                    f"Correct answer: {correct_answer}\n\n"
                    "Generate a follow-up question."
                )},
            ],
            max_tokens=128,
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("[LLM] Prove-it generation failed: %s", exc)
        return None
