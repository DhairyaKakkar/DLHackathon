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


class LLMSlide(BaseModel):
    type: Literal["concept", "analogy", "example", "code", "summary"]
    title: str
    body: str
    visual: Optional[str] = None   # code snippet for 'code' slides, null otherwise

    @field_validator("title", "body")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


class LLMLessonQuiz(BaseModel):
    question_type: Literal["MCQ", "SHORT_TEXT"]
    question_text: str
    options: Optional[list[str]] = None
    correct_option: Optional[str] = None
    rubric: Optional[list[str]] = None
    difficulty: int = 2

    @field_validator("difficulty")
    @classmethod
    def clamp(cls, v: int) -> int:
        return max(1, min(5, v))


class LLMLesson(BaseModel):
    topic: str
    slides: list[LLMSlide]
    quiz: list[LLMLessonQuiz]

    @field_validator("slides")
    @classmethod
    def need_slides(cls, v: list) -> list:
        if len(v) < 3:
            raise ValueError("need at least 3 slides")
        return v

    @field_validator("quiz")
    @classmethod
    def need_quiz(cls, v: list) -> list:
        if not v:
            raise ValueError("need at least 1 quiz question")
        return v[:2]


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


# ─── Topic Roadmap ────────────────────────────────────────────────────────────

class LLMResource(BaseModel):
    title: str
    url: str
    type: Literal["video", "article", "practice", "course", "documentation"]
    description: str

    @field_validator("title", "url", "description")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


class LLMStudyStep(BaseModel):
    number: int
    title: str
    description: str
    duration: str   # e.g. "2–3 days"

    @field_validator("title", "description", "duration")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


class LLMTopicRoadmap(BaseModel):
    diagnosis: str          # 2-3 sentences: why they're struggling (based on metric pattern)
    steps: list[LLMStudyStep]   # 3-5 ordered study steps
    resources: list[LLMResource]  # 4-6 real resources with working URLs
    concepts: list[str]     # 4-8 key concepts to focus on
    estimated_weeks: int    # to reach DUS ≥ 80

    @field_validator("steps")
    @classmethod
    def need_steps(cls, v: list) -> list:
        if len(v) < 2:
            raise ValueError("need at least 2 steps")
        return v[:6]

    @field_validator("resources")
    @classmethod
    def need_resources(cls, v: list) -> list:
        if not v:
            raise ValueError("need at least 1 resource")
        return v[:8]

    @field_validator("concepts")
    @classmethod
    def need_concepts(cls, v: list) -> list:
        if not v:
            raise ValueError("need at least 1 concept")
        return v[:10]


_ROADMAP_SYSTEM = """\
You are an expert learning coach. A student's EALE metrics for a specific topic are given.
Generate a personalised improvement roadmap as a JSON object.

EALE metric meanings:
- Mastery (0-100): recent accuracy on original questions
- Retention (0-100): accuracy across time gaps (spaced recall)
- Transfer (0-100): accuracy on rephrased/variant questions (generalisation)
- Calibration (0-100): confidence-accuracy alignment (100 = perfectly calibrated)
- DUS (0-100): weighted composite: 0.30*M + 0.30*R + 0.25*T + 0.15*C

Diagnose based on the weakest metric(s) — be specific (e.g. low retention = forgetting curve issue, low transfer = surface memorisation, low calibration = overconfidence).

For resources, provide REAL urls that work — prefer:
- YouTube: https://www.youtube.com/results?search_query=<topic+keyword> (always valid)
- Wikipedia: https://en.wikipedia.org/wiki/<Topic>
- GeeksforGeeks, Khan Academy, Coursera, MIT OpenCourseWare, LeetCode, CS50, Brilliant.org
- Use actual known page URLs when confident, YouTube search URLs otherwise

Return ONLY valid JSON (no markdown, no fences):
{
  "diagnosis": "<2-3 sentences explaining why they're struggling based on the specific weak metrics>",
  "steps": [
    {"number": 1, "title": "<action title>", "description": "<what to do and why>", "duration": "<e.g. 2-3 days>"},
    ...
  ],
  "resources": [
    {"title": "<resource name>", "url": "<real url>", "type": "video|article|practice|course|documentation", "description": "<one sentence: what this teaches>"},
    ...
  ],
  "concepts": ["<concept 1>", "<concept 2>", ...],
  "estimated_weeks": <integer 1-8>
}

Rules:
- steps: 3-5 items, ordered from immediate to long-term
- resources: 4-6 items, mix of types (at least 1 video, 1 practice)
- concepts: 4-8 specific sub-concepts the student should master
- estimated_weeks: realistic estimate to reach DUS 80 given current scores
- Tailor EVERYTHING to the specific topic name and weak metric pattern
"""


def generate_topic_roadmap(
    topic_name: str,
    mastery: float,
    retention: float,
    transfer: float,
    calibration: float,
    dus: float,
) -> Optional[LLMTopicRoadmap]:
    """
    Call GPT-4o to generate a personalised improvement roadmap for one topic.
    Returns None on any failure.
    """
    if not settings.OPENAI_API_KEY:
        return None

    user_msg = (
        f"Topic: {topic_name}\n\n"
        f"Student metrics:\n"
        f"  Mastery:     {mastery:.1f}/100\n"
        f"  Retention:   {retention:.1f}/100\n"
        f"  Transfer:    {transfer:.1f}/100\n"
        f"  Calibration: {calibration:.1f}/100\n"
        f"  DUS:         {dus:.1f}/100\n\n"
        "Generate a personalised improvement roadmap for this student."
    )

    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",          # always use gpt-4o for roadmap quality
            messages=[
                {"role": "system", "content": _ROADMAP_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            response_format={"type": "json_object"},
            max_tokens=1200,
            temperature=0.5,
        )
        raw = resp.choices[0].message.content
        result = LLMTopicRoadmap.model_validate_json(raw)
        logger.info("[LLM] Roadmap generated for topic=%r dus=%.1f", topic_name, dus)
        return result

    except ValidationError as exc:
        logger.warning("[LLM] Roadmap schema invalid: %s", exc)
        return None
    except Exception as exc:
        logger.warning("[LLM] Roadmap generation failed (%s): %s", type(exc).__name__, exc)
        return None


# ─── Learn It — Animated Video Lesson ────────────────────────────────────────

class LLMVideoLesson(BaseModel):
    topic: str
    html: str = ""       # self-contained HTML animation (empty when Sora is used)
    narration: str       # spoken narration script (used for TTS)
    audio_b64: str       # OpenAI TTS-1-HD MP3, base64-encoded
    quiz: list[LLMLessonQuiz]
    video_b64: str = ""  # Sora-generated MP4, base64-encoded (empty if HTML fallback)
    video_type: str = "html_animation"  # "sora_mp4" | "html_animation"
    scenes: list["LLMVideoScene"] = []

    @field_validator("quiz")
    @classmethod
    def need_quiz(cls, v: list) -> list:
        if not v:
            raise ValueError("need at least 1 quiz question")
        return v[:2]


class LLMLessonScenePlan(BaseModel):
    title: str
    caption: str
    narration: str
    visual_goal: str
    animation_beats: list[str]
    duration_seconds: int = 8

    @field_validator("title", "caption", "narration", "visual_goal")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()

    @field_validator("animation_beats")
    @classmethod
    def valid_beats(cls, v: list[str]) -> list[str]:
        cleaned = [item.strip() for item in v if item and item.strip()]
        if len(cleaned) < 2:
            raise ValueError("need at least 2 animation beats")
        return cleaned[:4]

    @field_validator("duration_seconds")
    @classmethod
    def clamp_duration(cls, v: int) -> int:
        return max(6, min(10, int(v)))


class LLMStoryboard(BaseModel):
    topic: str
    style_bible: str
    scenes: list[LLMLessonScenePlan]
    quiz: list[LLMLessonQuiz]

    @field_validator("topic", "style_bible")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()

    @field_validator("scenes")
    @classmethod
    def need_scenes(cls, v: list[LLMLessonScenePlan]) -> list[LLMLessonScenePlan]:
        if len(v) < 3:
            raise ValueError("need at least 3 scenes")
        return v[:4]

    @field_validator("quiz")
    @classmethod
    def need_quiz(cls, v: list[LLMLessonQuiz]) -> list[LLMLessonQuiz]:
        if not v:
            raise ValueError("need at least 1 quiz question")
        return v[:2]


class LLMVideoScene(BaseModel):
    title: str
    caption: str
    narration: str
    audio_b64: str = ""
    video_b64: str = ""
    duration_seconds: int = 8

    @field_validator("title", "caption", "narration")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


LLMVideoLesson.model_rebuild()


_LESSON_STORYBOARD_SYSTEM = """\
You are a world-class instructional director and curriculum designer.
Plan a premium micro-lesson that will later be rendered as multiple short Sora clips.

Return ONLY a valid JSON object with this exact shape:
{
  "topic": "<specific topic name, 2-5 words>",
  "style_bible": "<one short paragraph describing the shared visual language across all scenes>",
  "scenes": [
    {
      "title": "<2-4 words>",
      "caption": "<one sentence shown under the video>",
      "narration": "<spoken voiceover for this scene only>",
      "visual_goal": "<what the animation must visually make obvious>",
      "animation_beats": ["<beat 1>", "<beat 2>", "<beat 3>"],
      "duration_seconds": 8
    }
  ],
  "quiz": [
    {
      "question_type": "MCQ",
      "question_text": "<question testing understanding of the lesson>",
      "options": ["option A", "option B", "option C", "option D"],
      "correct_option": "<exact option text>",
      "rubric": null,
      "difficulty": 2
    },
    {
      "question_type": "SHORT_TEXT",
      "question_text": "<open-ended question requiring explanation in own words>",
      "options": null,
      "correct_option": null,
      "rubric": ["<criterion 1>", "<criterion 2>"],
      "difficulty": 3
    }
  ]
}

Rules:
- Create exactly 4 scenes.
- The scenes must progress in this order: intuition, mechanism, worked example, takeaway.
- Every scene must teach a different sub-idea. No repeated visuals. No recycled animations.
- narration must sound natural when spoken aloud and fit comfortably inside one short scene.
- narration should usually be 16-30 words per scene, 1-2 short sentences max.
- visual_goal must be concrete and visual, not abstract.
- animation_beats must describe motion, not static objects.
- style_bible should keep continuity across scenes but still allow each scene to look distinct.
- quiz questions must test understanding, not surface recall.
"""

_SORA_SCENE_PROMPT_SYSTEM = """\
You write elite Sora prompts for educational animations.
Turn the provided lesson scene into ONE polished prompt for a single cinematic clip.

Hard requirements:
- The clip must feel purposeful from beginning to end, not like a looping wallpaper.
- It must have a clear visual arc: opening state -> transformation -> resolved end frame.
- Absolutely avoid generic repeated motions, duplicated mini-animations, or meaningless particles.
- No talking heads, no classroom footage, no stock-video feel, no slideshow, no text-heavy screen.
- Use diagrams, geometry, motion, highlighting, labels, and camera movement only when they teach.
- Keep visual continuity with the shared style bible, but make this scene visually distinct from prior scenes.
- Make the central concept obvious even with audio muted.
- Mention exact motion, spatial layout, color accents, and what changes over time.
- End on a stable, elegant frame rather than resetting.

Return ONLY the final Sora prompt text. No JSON. No markdown.
"""

_VIDEO_LESSON_HTML_SYSTEM = """\
You are a world-class educational animator — think 3Blue1Brown, Khan Academy, and MIT OpenCourseWare combined.
Produce a COMPLETE, self-contained HTML file: a cinematic 80-second animated lesson.
Displayed in a 900×600px window (fullscreen capable). Auto-plays immediately. ZERO user interaction required.

━━━ STRUCTURE ━━━
4 scenes × 20 seconds each = 80 seconds total.
Use requestAnimationFrame for all animations (smooth 60fps).
Scene transitions: 1s cross-fade via CSS opacity.
Global progress bar at bottom fills 0→100% over 80s.

━━━ EACH SCENE MUST HAVE ━━━
1. A scene label chip (e.g. "01 / INTUITION") — top-left, small caps
2. A bold headline (18–22px)
3. A FULL-WIDTH CANVAS (860×260px) with a live, running animation specific to the topic
4. 1–2 lines of caption text below the canvas

━━━ CANVAS ANIMATION QUALITY — THIS IS THE MOST IMPORTANT PART ━━━
Every canvas must run a smooth, purpose-built animation using requestAnimationFrame. Examples:

• Projectile / physics: animate a ball along a parabolic arc; draw velocity vectors Vx (horizontal arrow,
  constant) and Vy (vertical arrow, shrinking then flipping); label with equations; show trajectory trail

• Sorting (bubble/merge/quick): animate colored bars; highlight comparisons in yellow, swaps in red;
  show pass counter; smooth height transitions

• Binary search: draw array boxes; animate a "pointer" arrow moving left/right; highlight mid in indigo,
  eliminated half in grey; show iteration counter

• Binary tree / BST: draw nodes as circles with values; animate traversal by highlighting nodes one by one
  in sequence; draw edges as lines; show current path

• Big-O complexity: draw a coordinate grid; animate curves growing (O(1) flat, O(log n), O(n), O(n²))
  with labels; highlight current topic's curve

• Neural network / ML: animate nodes lighting up layer by layer; show weight connections as lines
  brightening; display loss decreasing

• Calculus / derivatives: draw a curve (e.g. x²); animate a tangent line sweeping along it; show slope
  value changing; fill area under curve with gradient

• Recursion / call stack: animate boxes stacking (push) then unstacking (pop); show function name and
  argument in each box; highlight active frame

• Hash table: animate key → hash function → bucket index; show collision chaining; highlight probing

• Linked list: animate pointer arrows moving node to node; show insert/delete by unlinking and relinking

• For ANY other topic: invent the most visually compelling animated diagram that makes the concept click.
  Use particle systems, wave animations, gradient flows — whatever is most insightful.

━━━ VISUAL STYLE ━━━
Background: #050d1a (deep space black)
Text: #e2e8f0
Accent palette per scene: [#818cf8, #fb923c, #34d399, #f87171] (indigo, orange, green, red)
Canvas background: #0f172a with subtle grid lines (#1e293b, 1px)
Animated elements: bright fills (#818cf8, #fbbf24, #34d399) with glow (box-shadow or canvas shadowBlur=15)
Typography: 'Segoe UI', system-ui (no CDN). Scene label: 10px, letter-spacing 0.15em, opacity 0.5
Progress bar: 3px, gradient from accent[0] to accent[3]

━━━ CODE QUALITY ━━━
- All state in const/let at top of <script>
- Each scene has its own animate_sceneN() function using requestAnimationFrame
- Cancel previous animation frame when switching scenes (store frameId, call cancelAnimationFrame)
- Canvas: clear with fillRect each frame; use ctx.save()/ctx.restore() around transforms
- Smooth interpolation: use lerp() — const lerp = (a,b,t) => a + (b-a)*t
- Time-based animation: use (Date.now() - sceneStartTime) / sceneDuration for t (0→1)

━━━ HARD CONSTRAINTS ━━━
- Self-contained: ALL CSS + JS inline. Zero external dependencies. No CDN. No fetch().
- Works in sandbox="allow-scripts" iframe
- No alert(), confirm(), prompt(), document.cookie, localStorage
- canvas elements must have explicit width and height attributes
- HTML must be complete and valid — opening and closing tags balanced

RETURN ONLY THE RAW HTML. No markdown fences, no explanation, no commentary.
"""

_TRANSCRIPT_SUMMARY_SYSTEM = """\
You are preparing source material for a premium educational explainer video.
Compress the transcript/context into a dense but clean teaching brief.

Return ONLY plain text in this format:
Topic:
<one line>

Core ideas:
- ...
- ...

Key sequence:
1. ...
2. ...
3. ...

Important examples:
- ...
- ...

Misconceptions to correct:
- ...
- ...

Visual opportunities:
- ...
- ...

Rules:
- Prioritize what would make a great short explainer lesson.
- Remove filler, greetings, sponsor content, repetition, and digressions.
- Keep concrete terminology, equations, and examples if they matter.
- Make the result compact but information-dense.
"""

_TECHNICAL_LESSON_CLASSIFIER_SYSTEM = """\
You are deciding whether a topic is better taught by deterministic diagrams/animation than by a generative cinematic video clip.
Return ONLY JSON: {"prefer_html_animation": true|false, "reason": "<short reason>"}.

Prefer HTML animation when the content is technical, structured, diagram-heavy, algorithmic, mathematical, code-centric, or stepwise.
Prefer Sora only when the concept is mainly visual, physical, intuitive, narrative, or metaphor-friendly.
"""

def _generate_storyboard(client, user_context: str) -> LLMStoryboard:
    import json as _json

    resp = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _LESSON_STORYBOARD_SYSTEM},
            {"role": "user", "content": user_context},
        ],
        response_format={"type": "json_object"},
        max_tokens=1400,
        temperature=0.45,
    )
    raw = _json.loads(resp.choices[0].message.content)
    return LLMStoryboard.model_validate(raw)


def _write_sora_scene_prompt(
    client,
    topic: str,
    style_bible: str,
    scene: LLMLessonScenePlan,
    scene_index: int,
    scene_count: int,
) -> str:
    previous = "None" if scene_index == 0 else f"Previous scenes already covered scenes 1-{scene_index}."
    user_context = (
        f"Topic: {topic}\n"
        f"Scene number: {scene_index + 1} of {scene_count}\n"
        f"Shared style bible: {style_bible}\n"
        f"Scene title: {scene.title}\n"
        f"Caption: {scene.caption}\n"
        f"Narration: {scene.narration}\n"
        f"Visual goal: {scene.visual_goal}\n"
        f"Animation beats:\n- " + "\n- ".join(scene.animation_beats) + "\n"
        f"Context: {previous}\n"
        "Write the exact prompt for this scene."
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SORA_SCENE_PROMPT_SYSTEM},
            {"role": "user", "content": user_context},
        ],
        max_tokens=320,
        temperature=0.55,
    )
    return resp.choices[0].message.content.strip()


def _try_sora_video(client, prompt: str, clip_label: str) -> Optional[str]:
    """
    Try to generate a Sora video clip. Returns base64-encoded MP4 bytes, or None on any failure.
    Polls up to 240 seconds; falls back silently if Sora is unavailable or times out.
    """
    import base64
    import time as _time

    logger.info("[Sora] %s prompt: %.160s…", clip_label, prompt)

    # Create video generation job
    generation = client.video.generations.create(
        model="sora",
        prompt=prompt,
        size="1280x720",
        n=1,
    )
    gen_id = generation.id
    logger.info("[Sora] %s job created: id=%s status=%s", clip_label, gen_id, generation.status)

    # Poll until completed / failed / timed out
    deadline = _time.monotonic() + 240
    while generation.status not in ("completed", "failed", "cancelled"):
        if _time.monotonic() > deadline:
            logger.warning("[Sora] %s timed out waiting for job %s", clip_label, gen_id)
            return None
        _time.sleep(6)
        generation = client.video.generations.retrieve(gen_id)
        logger.info("[Sora] %s polling id=%s status=%s", clip_label, gen_id, generation.status)

    if generation.status != "completed":
        logger.warning("[Sora] %s job %s finished with status: %s", clip_label, gen_id, generation.status)
        return None

    # Download MP4 content
    content_resp = client.video.generations.content.retrieve(gen_id)
    video_bytes = content_resp.content  # raw bytes
    logger.info("[Sora] %s downloaded %d bytes for job %s", clip_label, len(video_bytes), gen_id)
    return base64.b64encode(video_bytes).decode("utf-8")


def _generate_html_animation(client, user_context: str) -> str:
    """Fallback: GPT-4o generates a self-contained canvas HTML animation."""
    html_resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _VIDEO_LESSON_HTML_SYSTEM},
            {"role": "user",   "content": user_context},
        ],
        max_tokens=8000,
        temperature=0.4,
    )
    animation_html = html_resp.choices[0].message.content.strip()
    # Strip markdown fences if GPT wraps in ```html ... ```
    if animation_html.startswith("```"):
        lines = animation_html.split("\n")
        animation_html = "\n".join(
            lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        )
    return animation_html


def _chunk_text(text: str, chunk_size: int = 6000, overlap: int = 500) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - overlap, 0)
    return chunks


def _distill_lesson_context(client, topic: str, raw_context: str) -> str:
    chunks = _chunk_text(raw_context, chunk_size=6000, overlap=500)
    partials: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _TRANSCRIPT_SUMMARY_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Topic hint: {topic}\n"
                        f"Transcript/context chunk {idx}/{len(chunks)}:\n{chunk}"
                    ),
                },
            ],
            max_tokens=700,
            temperature=0.2,
        )
        partials.append(resp.choices[0].message.content.strip())

    if len(partials) == 1:
        return partials[0]

    merged = "\n\n".join(partials)
    resp = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _TRANSCRIPT_SUMMARY_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Topic hint: {topic}\n"
                    "Merge these chunk summaries into one final teaching brief.\n\n"
                    f"{merged}"
                ),
            },
        ],
        max_tokens=900,
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def _should_prefer_html_animation(client, topic: str, distilled_context: str) -> bool:
    try:
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _TECHNICAL_LESSON_CLASSIFIER_SYSTEM},
                {
                    "role": "user",
                    "content": f"Topic: {topic}\n\nTeaching brief:\n{distilled_context[:5000]}",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=120,
            temperature=0.1,
        )
        import json as _json

        raw = _json.loads(resp.choices[0].message.content)
        prefer_html = bool(raw.get("prefer_html_animation"))
        logger.info("[LLM] Lesson render strategy: prefer_html=%s reason=%s", prefer_html, raw.get("reason"))
        return prefer_html
    except Exception as exc:
        logger.info("[LLM] Render strategy classifier failed: %s", exc)
        return False


def generate_video_lesson(
    topic: str,
    page_context: str = "",
    question_text: Optional[str] = None,
) -> Optional["LLMVideoLesson"]:
    """
    Generate a video lesson with TTS narration + 2 quiz questions.

    Tries Sora first (actual video), falls back to GPT-4o HTML animation silently.
    Always generates TTS narration and quiz questions.

    Returns None on any unrecoverable failure — caller should raise HTTP 503.
    """
    import base64

    if not settings.OPENAI_API_KEY:
        return None

    context_parts: list[str] = [f"Topic: {topic}"]
    if question_text:
        context_parts.append(f"The student just got this wrong: {question_text}")
    if page_context:
        context_parts.append(f"Page context:\n{page_context[:1500]}")
    user_context = "\n".join(context_parts)

    try:
        client = _openai_client()
        raw_lesson_context = page_context[:24000] if page_context else topic
        distilled_context = _distill_lesson_context(client, topic, raw_lesson_context)
        wrong_question_line = f"The student just got this wrong: {question_text}\n" if question_text else ""
        lesson_context = (
            f"Topic: {topic}\n"
            f"{wrong_question_line}"
            f"Teaching brief:\n{distilled_context}"
        )
        is_youtube_lesson = "[YouTube transcript]" in page_context
        prefer_html_animation = is_youtube_lesson or _should_prefer_html_animation(client, topic, distilled_context)

        storyboard = _generate_storyboard(client, lesson_context)
        detected_topic = storyboard.topic
        full_narration = " ".join(scene.narration for scene in storyboard.scenes)

        # ── Attempt 1: multi-scene Sora lesson ───────────────────────────────
        video_b64: str = ""
        audio_b64: str = ""
        video_type: str = "html_animation"
        animation_html: str = ""
        video_scenes: list[LLMVideoScene] = []

        if not prefer_html_animation:
            try:
                for idx, scene in enumerate(storyboard.scenes):
                    sora_prompt = _write_sora_scene_prompt(
                        client=client,
                        topic=detected_topic,
                        style_bible=storyboard.style_bible,
                        scene=scene,
                        scene_index=idx,
                        scene_count=len(storyboard.scenes),
                    )
                    clip_label = f"scene_{idx + 1}"
                    clip_b64 = _try_sora_video(client, sora_prompt, clip_label) or ""
                    if not clip_b64:
                        raise RuntimeError(f"Sora failed for {clip_label}")

                    tts_resp = client.audio.speech.create(
                        model="tts-1-hd",
                        voice="nova",
                        input=scene.narration,
                    )
                    scene_audio_b64 = base64.b64encode(tts_resp.read()).decode("utf-8")
                    video_scenes.append(
                        LLMVideoScene(
                            title=scene.title,
                            caption=scene.caption,
                            narration=scene.narration,
                            audio_b64=scene_audio_b64,
                            video_b64=clip_b64,
                            duration_seconds=scene.duration_seconds,
                        )
                    )

                if len(video_scenes) >= 3:
                    video_type = "sora_scene_playlist"
                    # Keep legacy top-level fields populated with scene 1 for compatibility.
                    video_b64 = video_scenes[0].video_b64
                    audio_b64 = video_scenes[0].audio_b64
                    logger.info("[LLM] Sora scene playlist generated (%d scenes)", len(video_scenes))
            except Exception as sora_exc:
                logger.info(
                    "[Sora] Scene playlist unavailable (%s: %s) — falling back to HTML animation",
                    type(sora_exc).__name__, sora_exc,
                )
                video_scenes = []
        else:
            logger.info("[LLM] Skipping Sora and using HTML animation as primary renderer")

        # ── Fallback: GPT-4o HTML animation ──────────────────────────────────
        if not video_scenes:
            storyboard_summary = "\n".join(
                f"Scene {i + 1} - {scene.title}: {scene.visual_goal}. Beats: {', '.join(scene.animation_beats)}"
                for i, scene in enumerate(storyboard.scenes)
            )
            animation_html = _generate_html_animation(
                client,
                (
                    f"{lesson_context}\n\n"
                    f"Storyboard:\n{storyboard_summary}\n\n"
                    f"Style bible:\n{storyboard.style_bible}\n\n"
                    "Render this as a premium educational animation with precise concept-first visuals."
                ),
            )
            logger.info("[LLM] HTML animation generated (%d chars)", len(animation_html))
            tts_resp = client.audio.speech.create(
                model="tts-1-hd",
                voice="nova",
                input=full_narration or f"Let's learn about {topic}.",
            )
            audio_b64 = base64.b64encode(tts_resp.read()).decode("utf-8")

        logger.info(
            "[LLM] Lesson generated: topic=%r type=%s quiz=%d",
            detected_topic, video_type, len(storyboard.quiz),
        )
        return LLMVideoLesson(
            topic=detected_topic,
            html=animation_html,
            narration=full_narration,
            audio_b64=audio_b64,
            quiz=storyboard.quiz,
            video_b64=video_b64,
            video_type=video_type,
            scenes=video_scenes,
        )

    except ValidationError as exc:
        logger.warning("[LLM] Video lesson schema invalid: %s", exc)
        return None
    except Exception as exc:
        logger.warning("[LLM] Video lesson generation failed (%s): %s", type(exc).__name__, exc)
        return None
