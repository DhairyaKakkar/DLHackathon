"""
Manim-based educational video generation service.

Pipeline:
  1. GPT-4o generates narration script + Manim scene code in one call
  2. Manim renders the animation to MP4 via subprocess (720p30)
     - Retry loop: up to 3 attempts, errors fed back to GPT-4o for auto-fix
  3. OpenAI TTS-1-HD generates narration audio
  4. FFmpeg muxes video + audio into final MP4
  5. Returns base64-encoded final video

No LaTeX required — uses Text() throughout, so the Docker image stays lean.
"""

import base64
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ValidationError

from app.config import settings

logger = logging.getLogger(__name__)


# ─── Output schema ────────────────────────────────────────────────────────────

@dataclass
class ManimLesson:
    topic: str
    video_b64: str        # base64 MP4 with audio muxed in
    audio_b64: str        # same narration audio separately (for UI volume control)
    narration: str
    video_type: str = "manim_mp4"


# ─── LLM response schema ──────────────────────────────────────────────────────

class _LessonPlan(BaseModel):
    narration: str
    manim_code: str


# ─── Prompts ──────────────────────────────────────────────────────────────────

_LESSON_SYSTEM = """\
You are an expert educational animator using the Manim Community Python library.
Your job: generate a 75–90 second animated explainer video scene for a student learning a topic.

══ STRICT RULES — ANY VIOLATION CAUSES RENDER FAILURE ══
1. Import ONLY:  from manim import *
2. NEVER use MathTex(), Tex(), SingleStringMathTex(), or any LaTeX — LaTeX is NOT installed.
   Use Text() for ALL text, including formulas. E.g., Text("O(log n)") not MathTex("O(\\log n)")
3. Class MUST be named exactly:  EALELesson  and extend  Scene  (not ThreeDScene)
4. self.wait() calls must total 70–90 seconds across the whole scene.
5. Every object must be added to scene with self.add() or self.play() before referencing it further.
6. Keep all objects within camera frame: x in [-6, 6], y in [-3.5, 3.5]
7. VGroup.arrange() is the safest way to lay out multiple objects.

══ ALLOWED MANIM OBJECTS ══
Text, VGroup, Group, Rectangle, Square, Circle, RoundedRectangle, Ellipse, Polygon,
Arrow, Line, DashedLine, CurvedArrow, Dot, Brace, SurroundingRectangle, Underline,
NumberLine, BarChart

══ ALLOWED ANIMATIONS ══
Write, FadeIn, FadeOut, Create, DrawBorderThenFill, GrowArrow, GrowFromCenter,
Transform, ReplacementTransform, Indicate, Flash, Circumscribe, ShowCreation,
.animate.move_to(), .animate.shift(), .animate.scale(), .animate.set_color(),
.animate.set_opacity(), ApplyMethod

══ SAFE COLORS ══
BLUE, RED, GREEN, YELLOW, WHITE, ORANGE, PURPLE, TEAL, GOLD, GRAY, BLACK,
DARK_BLUE, DARK_GREEN, LIGHT_BLUE, MAROON, BLUE_A, BLUE_B, BLUE_C, BLUE_D, BLUE_E,
RED_A, RED_B, RED_C, GREEN_A, GREEN_B, GREEN_C, YELLOW_A, YELLOW_B

══ BEST PATTERNS FOR CS/ALGORITHM CONTENT ══

Array visualization:
  boxes = VGroup(*[Rectangle(width=1, height=0.8).set_fill(BLUE, opacity=0.4) for _ in range(5)])
  boxes.arrange(RIGHT, buff=0.1)
  labels = VGroup(*[Text(str(i), font_size=24) for i in [3,1,4,1,5]])
  for l, b in zip(labels, boxes): l.move_to(b)

Tree nodes:
  node = Circle(radius=0.4).set_fill(TEAL, opacity=0.6)
  label = Text("root", font_size=20).move_to(node)
  edge = Arrow(start=node.get_bottom(), end=child.get_top())

Step-by-step reveal:
  steps = VGroup(Text("Step 1: ...", font_size=28), Text("Step 2: ...", font_size=28))
  steps.arrange(DOWN, aligned_edge=LEFT, buff=0.4)
  for step in steps:
      self.play(FadeIn(step)); self.wait(2)

Highlight active element:
  self.play(Indicate(box, color=YELLOW, scale_factor=1.3))

══ SCENE STRUCTURE (follow this) ══
1. Title card (5–8 s): Large centered title Text, Write animation, then move to top
2. Concept intro (20–25 s): Core idea with visual representation + annotations
3. Example walkthrough (30–40 s): Step-by-step animations with self.wait() between beats
4. Summary (8–12 s): Key takeaway text, FadeIn

══ OUTPUT FORMAT ══
Return ONLY valid JSON with exactly two keys:
{
  "narration": "<150–175 word script that takes 75–90 s to read aloud naturally>",
  "manim_code": "<complete Python script starting with: from manim import *>"
}

The narration should be structured to match the 4 animation beats above.
The manim_code must be complete, standalone, and runnable with no modification.
Do NOT include markdown fences or any text outside the JSON.
"""

_FIX_SYSTEM = """\
You are a Manim debugging expert. A generated Manim scene failed to render.
Fix ONLY the broken code — preserve the educational content and structure.

Rules (same as before):
- NEVER use MathTex, Tex, or any LaTeX
- Class must be EALELesson(Scene)
- All self.wait() calls must total 70–90 seconds
- Keep objects in camera bounds: x in [-6,6], y in [-3.5,3.5]
- Do not use ShowCreation if unavailable — use Create instead

Return ONLY the fixed Python code. No JSON wrapper. No markdown. No explanation.
"""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _generate_plan(
    topic: str,
    page_context: str,
    question_text: Optional[str],
) -> Optional[_LessonPlan]:
    """Call GPT-4o to generate narration + Manim code in one shot."""
    if not settings.OPENAI_API_KEY:
        return None

    context_block = ""
    if page_context:
        context_block += f"\n\nPage context (what the student was studying):\n{page_context[:1500]}"
    if question_text:
        context_block += f"\n\nThe student struggled with this question: {question_text}"

    user_msg = (
        f"Generate an educational Manim animation for this topic: {topic}"
        f"{context_block}\n\n"
        "Make it engaging, clear, and directly useful for a student who is struggling. "
        "Focus on intuition and concrete examples, not abstract theory."
    )

    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _LESSON_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            response_format={"type": "json_object"},
            max_tokens=3000,
            temperature=0.6,
        )
        raw = resp.choices[0].message.content
        plan = _LessonPlan.model_validate_json(raw)
        logger.info("[Manim] Plan generated: narration=%d chars, code=%d chars",
                    len(plan.narration), len(plan.manim_code))
        return plan
    except (ValidationError, Exception) as exc:
        logger.warning("[Manim] Plan generation failed: %s", exc)
        return None


def _fix_manim_code(code: str, error: str) -> Optional[str]:
    """Ask GPT-4o to fix broken Manim code given the render error."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _FIX_SYSTEM},
                {"role": "user", "content": (
                    f"The following Manim code failed with this error:\n\n"
                    f"ERROR:\n{error[-2500:]}\n\n"
                    f"BROKEN CODE:\n{code}\n\n"
                    "Fix it and return only the corrected Python code."
                )},
            ],
            max_tokens=2500,
            temperature=0.2,
        )
        fixed = resp.choices[0].message.content.strip()
        # Strip markdown fences if GPT-4o wraps it
        if fixed.startswith("```"):
            lines = fixed.split("\n")
            fixed = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        return fixed
    except Exception as exc:
        logger.warning("[Manim] Fix call failed: %s", exc)
        return None


def _validate_code(code: str) -> Optional[str]:
    """Quick sanity check before running Manim. Returns error string or None."""
    if "class EALELesson(Scene)" not in code:
        return "Missing 'class EALELesson(Scene)'"
    if "MathTex(" in code or "Tex(" in code:
        return "Code uses MathTex/Tex — LaTeX not installed"
    if "def construct(self)" not in code:
        return "Missing 'def construct(self)'"
    if "from manim import" not in code:
        return "Missing Manim import"
    return None


def _run_manim(code: str, tmpdir: str) -> tuple[bool, str, str]:
    """
    Write code to temp file, run Manim, return (success, mp4_path, stderr).
    Output will be at: {tmpdir}/output/videos/lesson/720p30/EALELesson.mp4
    """
    scene_file = os.path.join(tmpdir, "lesson.py")
    output_dir = os.path.join(tmpdir, "output")

    with open(scene_file, "w") as f:
        f.write(code)

    cmd = [
        "manim", "render",
        scene_file, "EALELesson",
        "--quality", "m",            # 720p30
        "--disable_caching",
        "--media_dir", output_dir,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=360,             # 6 min max render
            cwd=tmpdir,
        )
        stderr = result.stderr + result.stdout

        # Find the rendered MP4
        mp4_path = Path(output_dir) / "videos" / "lesson" / "720p30" / "EALELesson.mp4"
        if not mp4_path.exists():
            # Manim sometimes puts it in a slightly different path — search
            found = list(Path(output_dir).rglob("EALELesson.mp4"))
            if found:
                mp4_path = found[0]
            else:
                logger.warning("[Manim] MP4 not found after render. stderr:\n%s", stderr[-1500:])
                return False, "", stderr

        logger.info("[Manim] Rendered: %s (%d bytes)", mp4_path, mp4_path.stat().st_size)
        return True, str(mp4_path), stderr

    except subprocess.TimeoutExpired:
        logger.warning("[Manim] Render timed out after 360s")
        return False, "", "TimeoutExpired: render took longer than 6 minutes"
    except Exception as exc:
        logger.warning("[Manim] Render subprocess error: %s", exc)
        return False, "", str(exc)


def _generate_tts(narration: str) -> Optional[bytes]:
    """Generate TTS audio using OpenAI TTS-1-HD."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        client = _openai_client()
        resp = client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",
            input=narration,
            response_format="mp3",
        )
        audio_bytes = resp.read()
        logger.info("[Manim] TTS generated: %d bytes", len(audio_bytes))
        return audio_bytes
    except Exception as exc:
        logger.warning("[Manim] TTS failed: %s", exc)
        return None


def _mux_video_audio(video_path: str, audio_path: str, output_path: str) -> bool:
    """FFmpeg: combine silent Manim video + TTS narration into final MP4."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",             # cut at whichever stream ends first
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.warning("[Manim] FFmpeg mux failed:\n%s", result.stderr[-1000:])
            return False
        logger.info("[Manim] Muxed to %s", output_path)
        return True
    except Exception as exc:
        logger.warning("[Manim] FFmpeg error: %s", exc)
        return False


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_manim_lesson(
    topic: str,
    page_context: str = "",
    question_text: Optional[str] = None,
) -> Optional[ManimLesson]:
    """
    Full pipeline: GPT-4o plan → Manim render (with retry) → TTS → FFmpeg mux → base64.
    Returns None on any unrecoverable failure.
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("[Manim] No OPENAI_API_KEY — cannot generate lesson")
        return None

    # Step 1: Generate narration + Manim code
    plan = _generate_plan(topic, page_context, question_text)
    if not plan:
        return None

    manim_code = plan.manim_code
    narration = plan.narration

    with tempfile.TemporaryDirectory(prefix="eale_manim_") as tmpdir:
        mp4_path = ""
        last_error = ""

        # Step 2: Render with retry loop (up to 3 attempts)
        for attempt in range(3):
            # Quick validation before running Manim
            validation_error = _validate_code(manim_code)
            if validation_error:
                logger.warning("[Manim] Attempt %d: code validation failed: %s", attempt + 1, validation_error)
                last_error = validation_error
            else:
                success, mp4_path, last_error = _run_manim(manim_code, tmpdir)
                if success:
                    logger.info("[Manim] Rendered successfully on attempt %d", attempt + 1)
                    break
                logger.warning("[Manim] Attempt %d failed. Asking GPT-4o to fix...", attempt + 1)

            if attempt < 2:
                fixed = _fix_manim_code(manim_code, last_error)
                if fixed:
                    manim_code = fixed
                else:
                    logger.warning("[Manim] GPT-4o fix call failed — giving up")
                    return None
            else:
                logger.warning("[Manim] All 3 render attempts failed. Last error:\n%s", last_error[-800:])
                return None

        # Step 3: Generate TTS narration
        audio_bytes = _generate_tts(narration)
        if not audio_bytes:
            # Return video-only (no audio) rather than failing completely
            logger.warning("[Manim] TTS failed — returning silent video")
            with open(mp4_path, "rb") as f:
                video_b64 = base64.b64encode(f.read()).decode()
            return ManimLesson(
                topic=topic,
                video_b64=video_b64,
                audio_b64="",
                narration=narration,
            )

        # Step 4: Write audio to temp file and mux
        audio_path = os.path.join(tmpdir, "narration.mp3")
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        muxed_path = os.path.join(tmpdir, "final.mp4")
        mux_ok = _mux_video_audio(mp4_path, audio_path, muxed_path)

        # Use muxed if available, fallback to silent video
        final_path = muxed_path if mux_ok else mp4_path

        # Step 5: Base64 encode outputs
        with open(final_path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode()

        audio_b64 = base64.b64encode(audio_bytes).decode()

        logger.info(
            "[Manim] Lesson ready: video=%d KB audio=%d KB",
            len(video_b64) * 3 // 4 // 1024,
            len(audio_b64) * 3 // 4 // 1024,
        )

        return ManimLesson(
            topic=topic,
            video_b64=video_b64,
            audio_b64=audio_b64,
            narration=narration,
        )
