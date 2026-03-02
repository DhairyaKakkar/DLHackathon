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


# ─── Learn It — Animated Video Lesson ────────────────────────────────────────

class LLMVideoLesson(BaseModel):
    topic: str
    html: str = ""       # self-contained HTML animation (empty when Sora is used)
    narration: str       # spoken narration script (used for TTS)
    audio_b64: str       # OpenAI TTS-1-HD MP3, base64-encoded
    quiz: list[LLMLessonQuiz]
    video_b64: str = ""  # Sora-generated MP4, base64-encoded (empty if HTML fallback)
    video_type: str = "html_animation"  # "sora_mp4" | "html_animation"

    @field_validator("quiz")
    @classmethod
    def need_quiz(cls, v: list) -> list:
        if not v:
            raise ValueError("need at least 1 quiz question")
        return v[:2]


_SORA_PROMPT_SYSTEM = """\
You are a world-class educational video director creating a prompt for Sora (OpenAI's video AI).
Write a vivid, cinematic 8-second educational video prompt that will produce a stunning animated
visualization for the given topic.

Your prompt must describe:
- A smooth, flowing animation that makes the concept visually click
- Specific visual elements: animated diagrams, graphs, particles, geometric shapes, equations
- Cinematic quality: soft lens, gentle camera movements (slow zoom or pan), professional lighting
- Color palette: deep dark background (#050d1a or deep space black), vivid neon-like educational
  colors (electric blue, bright orange, glowing green, soft white text)
- Style: 3Blue1Brown / Grant Sanderson mathematical animation meets Pixar-level production

Great prompt examples:
- "Smooth cinematic animation of binary search: glowing blue array boxes, golden pointer arrow
  sweeps to middle element, eliminated halves dissolve to dark grey, active region gently zooms in,
  iteration counter increments, deep space background, professional educational visualization"
- "A glowing sphere traces a perfect parabolic arc against a dark starfield, real-time velocity
  vector arrows animate showing Vx (horizontal, constant) and Vy (vertical, shrinking then flipping),
  golden trajectory trail fades behind it, cinematic slow-motion at apex, physics labels appear
  with smooth fade-in, 3Blue1Brown style"

Return ONLY the Sora video prompt. No JSON. No preamble. Max 200 words.
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

_NARRATION_QUIZ_SYSTEM = """\
You are an expert educator. Return ONLY a valid JSON object (no markdown):
{
  "topic": "<specific topic name, 2-5 words>",
  "narration": "<spoken narration script for a 72-second animated lesson — 4 paragraphs of ~2 sentences each, one per scene. Natural, engaging voice as if speaking to a student>",
  "quiz": [
    {
      "question_type": "MCQ",
      "question_text": "<question testing understanding of a specific concept from this topic>",
      "options": ["option A", "option B", "option C", "option D"],
      "correct_option": "<exact string from options>",
      "rubric": null,
      "difficulty": 2
    },
    {
      "question_type": "SHORT_TEXT",
      "question_text": "<open-ended question requiring explanation in own words>",
      "options": null,
      "correct_option": null,
      "rubric": ["<key criterion 1>", "<key criterion 2>"],
      "difficulty": 3
    }
  ]
}
Rules:
- narration should flow naturally when read aloud; ~130-160 words total
- quiz questions must test understanding, not recall
- MCQ must have exactly 4 options with one correct_option matching exactly
"""


def _try_sora_video(client, user_context: str) -> Optional[str]:
    """
    Try to generate a Sora video. Returns base64-encoded MP4 bytes, or None on any failure.
    Polls up to 150 seconds; falls back silently if Sora is unavailable or times out.
    """
    import base64
    import time as _time

    # GPT-4o writes a cinematic Sora prompt
    prompt_resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SORA_PROMPT_SYSTEM},
            {"role": "user",   "content": user_context},
        ],
        max_tokens=300,
        temperature=0.6,
    )
    sora_prompt = prompt_resp.choices[0].message.content.strip()
    logger.info("[Sora] Prompt: %.120s…", sora_prompt)

    # Create video generation job
    generation = client.video.generations.create(
        model="sora",
        prompt=sora_prompt,
        size="1280x720",
        n=1,
    )
    gen_id = generation.id
    logger.info("[Sora] Job created: id=%s status=%s", gen_id, generation.status)

    # Poll until completed / failed / timed out
    deadline = _time.monotonic() + 150
    while generation.status not in ("completed", "failed", "cancelled"):
        if _time.monotonic() > deadline:
            logger.warning("[Sora] Timed out waiting for job %s", gen_id)
            return None
        _time.sleep(6)
        generation = client.video.generations.retrieve(gen_id)
        logger.info("[Sora] Polling id=%s status=%s", gen_id, generation.status)

    if generation.status != "completed":
        logger.warning("[Sora] Job %s finished with status: %s", gen_id, generation.status)
        return None

    # Download MP4 content
    content_resp = client.video.generations.content.retrieve(gen_id)
    video_bytes = content_resp.content  # raw bytes
    logger.info("[Sora] Downloaded %d bytes for job %s", len(video_bytes), gen_id)
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
    import json as _json

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

        # ── Attempt 1: Sora video ─────────────────────────────────────────────
        video_b64: str = ""
        video_type: str = "html_animation"
        animation_html: str = ""

        try:
            video_b64 = _try_sora_video(client, user_context) or ""
            if video_b64:
                video_type = "sora_mp4"
                logger.info("[LLM] Sora video generated (%d b64 chars)", len(video_b64))
        except Exception as sora_exc:
            logger.info(
                "[Sora] Not available (%s: %s) — falling back to HTML animation",
                type(sora_exc).__name__, sora_exc,
            )

        # ── Fallback: GPT-4o HTML animation ──────────────────────────────────
        if not video_b64:
            animation_html = _generate_html_animation(client, user_context)
            logger.info("[LLM] HTML animation generated (%d chars)", len(animation_html))

        # ── Narration + quiz (JSON) ────────────────────────────────────────────
        nq_resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _NARRATION_QUIZ_SYSTEM},
                {"role": "user",   "content": user_context},
            ],
            response_format={"type": "json_object"},
            max_tokens=600,
            temperature=0.4,
        )
        nq_raw = _json.loads(nq_resp.choices[0].message.content)
        detected_topic = nq_raw.get("topic", topic)
        narration_text = nq_raw.get("narration", "")
        raw_quiz = nq_raw.get("quiz", [])
        quiz = [LLMLessonQuiz.model_validate(q) for q in raw_quiz[:2]]

        # ── TTS narration ─────────────────────────────────────────────────────
        tts_resp = client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",
            input=narration_text or f"Let's learn about {topic}.",
        )
        audio_b64 = base64.b64encode(tts_resp.read()).decode("utf-8")

        logger.info(
            "[LLM] Lesson generated: topic=%r type=%s quiz=%d",
            detected_topic, video_type, len(quiz),
        )
        return LLMVideoLesson(
            topic=detected_topic,
            html=animation_html,
            narration=narration_text,
            audio_b64=audio_b64,
            quiz=quiz,
            video_b64=video_b64,
            video_type=video_type,
        )

    except ValidationError as exc:
        logger.warning("[LLM] Video lesson schema invalid: %s", exc)
        return None
    except Exception as exc:
        logger.warning("[LLM] Video lesson generation failed (%s): %s", type(exc).__name__, exc)
        return None
