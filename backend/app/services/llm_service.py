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


# ─── Public API ───────────────────────────────────────────────────────────────

def infer_topic_and_generate_question(
    url: str,
    title: str,
    text_snippet: str,
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

    user_msg = (
        f"Page URL: {url}\n"
        f"Page title: {title}\n\n"
        f"Content excerpt:\n{snippet}\n\n"
        "Generate a transfer-style question for this content."
    )

    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _QUESTION_SYSTEM},
                {"role": "user",   "content": user_msg},
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
