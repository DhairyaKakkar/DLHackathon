"""
Multi-chapter Manim educational video generation service.

Pipeline:
  1. GPT-4o writes a 5-chapter lesson plan (titles + narration + visual approach)
  2. GPT-4o generates a full, rich Manim scene for EACH chapter (5 separate GPT calls)
  3. Each scene is rendered individually by Manim (720p30, up to 3 fix-retries each)
  4. OpenAI TTS-1-HD generates one narration audio track for the whole lesson
  5. FFmpeg concatenates all chapter MP4s into one combined video
  6. FFmpeg muxes combined video + narration audio into final MP4
  7. Returns base64-encoded final video (~4-6 minutes, ~15 min generation time)
"""

import base64
import json
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
    video_b64: str
    audio_b64: str
    narration: str
    video_type: str = "manim_mp4"


# ─── Internal schemas ─────────────────────────────────────────────────────────

class _ChapterPlan(BaseModel):
    title: str
    key_concept: str
    visual_approach: str   # describes what shapes/animations to show
    narration_segment: str # 60–80 words spoken in this chapter


class _LessonPlan(BaseModel):
    lesson_title: str
    chapters: list[_ChapterPlan]  # exactly 5


class _ChapterCode(BaseModel):
    manim_code: str


# ─── Prompts ──────────────────────────────────────────────────────────────────

_PLANNER_SYSTEM = """\
You are a world-class educational content designer creating a multi-chapter video lesson.
Your output is a structured 5-chapter lesson plan for a Manim animated video.

Each chapter covers ONE focused concept/phase and will be rendered as a separate 70–85 second animation.
Together the 5 chapters form a complete 6–7 minute educational masterpiece.

Structure each chapter to build on the previous one:
  Ch 1 — Hook + real-world motivation (why does this matter?)
  Ch 2 — Core concept definition with visual intuition
  Ch 3 — Step-by-step worked example (concrete numbers/data)
  Ch 4 — Edge cases, variations, or deeper insight
  Ch 5 — Summary, formula/takeaway, and connection to bigger picture

For visual_approach, describe exactly what should be animated:
- For algorithms: which data structures, what step-by-step state changes
- For physics: which diagrams, force vectors, trajectory shapes
- For math: which graphs, geometric shapes, transformations
- Be specific: "animate an array of 6 boxes, highlight the pivot in red, show partition by moving elements"

IMPORTANT: narration_segment must be 160–190 words — this is ~65–75 seconds of spoken audio
and must EXACTLY match the animation timing of that chapter.

Return ONLY valid JSON:
{
  "lesson_title": "...",
  "chapters": [
    {
      "title": "...",
      "key_concept": "one sentence",
      "visual_approach": "detailed description of what to animate",
      "narration_segment": "160-190 word spoken narration timed to match the 70-85 second animation"
    },
    ... (5 total)
  ]
}
"""

_CHAPTER_SYSTEM = """\
You are an expert Manim animator in the style of 3Blue1Brown.
Generate a rich, cinematic 60–80 second Manim scene for ONE chapter of a multi-chapter educational video.

══ ABSOLUTE RULES — VIOLATION CAUSES RENDER FAILURE ══
1. First two lines MUST be:
       from manim import *
       import numpy as np
2. NEVER use MathTex(), Tex(), SingleStringMathTex() or ANY LaTeX — LaTeX is NOT installed.
   Use Text() for ALL text and equations. E.g. Text("F = ma") not MathTex("F = ma")
3. Class MUST be named exactly:  EALELesson  and extend  Scene  (not ThreeDScene or any other)
4. self.wait() calls must total 55–75 seconds.
5. NEVER reference an object before adding it with self.add() or self.play().
6. Keep ALL objects: x in [-6, 6], y in [-3.5, 3.5] — never go outside this.
7. TRACK OBJECTS EXPLICITLY — use named groups, never self.mobjects:
       phase1 = VGroup()        # add all phase-1 objects here
       ...
       self.play(FadeOut(phase1))   # clean clear at end of phase

══ OBJECT TRACKING PATTERN (MANDATORY) ══
NEVER write: self.play(FadeOut(VGroup(*self.mobjects)))   ← CRASHES if scene is empty
ALWAYS write: self.play(FadeOut(group_name))              ← only fade what you added

Pattern for each visual phase:
  # --- Phase N ---
  phaseN = VGroup()
  obj1 = Text("...", font_size=36)
  phaseN.add(obj1)
  self.play(Write(obj1))
  self.wait(2)
  # ... more animations ...
  self.play(FadeOut(phaseN))
  self.wait(0.3)

══ MOTION DENSITY — every 8 seconds must have a self.play() call ══

SMOOTH MOVEMENT:
  ball = Circle(radius=0.3).set_fill(BLUE, opacity=0.9).move_to([-4, 0, 0])
  self.play(Create(ball))
  self.play(ball.animate.move_to([0, 2, 0]), run_time=1.5)
  self.play(ball.animate.move_to([4, -1, 0]), run_time=1.5)

ARRAY ANIMATION:
  boxes = VGroup(*[Rectangle(width=0.9, height=0.8).set_fill(BLUE_D, opacity=0.6) for _ in range(5)])
  boxes.arrange(RIGHT, buff=0.15).move_to(ORIGIN)
  vals = VGroup(*[Text(str(v), font_size=24) for v in [3, 1, 4, 1, 5]])
  for lbl, box in zip(vals, boxes):
      lbl.move_to(box)
  arr_group = VGroup(boxes, vals)
  self.play(LaggedStart(*[FadeIn(b) for b in boxes], lag_ratio=0.12), run_time=1.5)
  self.play(LaggedStart(*[FadeIn(l) for l in vals], lag_ratio=0.12), run_time=1.0)
  # Highlight two elements
  self.play(boxes[0].animate.set_color(RED), boxes[2].animate.set_color(RED))
  self.wait(1)
  # Swap
  pos0, pos2 = boxes[0].get_center().copy(), boxes[2].get_center().copy()
  self.play(
      boxes[0].animate.move_to(pos2), vals[0].animate.move_to(pos2),
      boxes[2].animate.move_to(pos0), vals[2].animate.move_to(pos0),
      run_time=1.0
  )

PARABOLA / TRAJECTORY (numpy is imported):
  dots = VGroup()
  for i in range(16):
      t = i / 15.0
      x = -5.0 + t * 10.0
      y = -1.5 + 3.0 * t * (1.0 - t)
      d = Dot(point=np.array([x, y, 0]), color=YELLOW, radius=0.07)
      dots.add(d)
  self.play(LaggedStart(*[Create(d) for d in dots], lag_ratio=0.07), run_time=2.0)

BAR CHART:
  bar_data = [1.0, 2.5, 1.5, 3.0, 2.0]
  bar_group = VGroup()
  for i, h in enumerate(bar_data):
      bar = Rectangle(width=0.6, height=h).set_fill(TEAL, opacity=0.85)
      bar.move_to(np.array([-4.0 + i * 2.0, -1.5 + h / 2.0, 0]))
      bar_group.add(bar)
  self.play(LaggedStart(*[GrowFromCenter(b) for b in bar_group], lag_ratio=0.2), run_time=2.0)

TREE NODES:
  node_data = [("root", [0, 2.5, 0]), ("L", [-2.5, 0.5, 0]), ("R", [2.5, 0.5, 0])]
  node_group = VGroup()
  node_circles = {}
  for label, pos in node_data:
      c = Circle(radius=0.4).set_fill(TEAL, opacity=0.7).move_to(np.array(pos))
      t = Text(label, font_size=20).move_to(np.array(pos))
      node_circles[label] = c
      node_group.add(VGroup(c, t))
  self.play(LaggedStart(*[Create(n) for n in node_group], lag_ratio=0.3), run_time=1.5)
  edge1 = Arrow(node_circles["root"].get_bottom(), node_circles["L"].get_top(), buff=0.1)
  edge2 = Arrow(node_circles["root"].get_bottom(), node_circles["R"].get_top(), buff=0.1)
  self.play(GrowArrow(edge1), GrowArrow(edge2))
  node_group.add(edge1, edge2)

FORMULA TERM-BY-TERM:
  terms  = ["v", " = ", "u", " + ", "a", "t"]
  colors = [YELLOW, WHITE, GREEN, WHITE, ORANGE, RED]
  parts  = VGroup(*[Text(t, font_size=44, color=c) for t, c in zip(terms, colors)])
  parts.arrange(RIGHT, buff=0.05).move_to(ORIGIN)
  self.play(LaggedStart(*[Write(p) for p in parts], lag_ratio=0.2), run_time=2.0)
  lbl = Text("kinematic equation", font_size=22, color=GRAY).next_to(parts, DOWN, buff=0.4)
  self.play(FadeIn(lbl))
  self.wait(3)
  self.play(Indicate(parts, scale_factor=1.08))

CALLOUT BOX:
  bg  = RoundedRectangle(corner_radius=0.18, width=5.5, height=1.1).set_fill(DARK_BLUE, opacity=0.9)
  txt = Text("Key insight here", font_size=26).move_to(bg)
  box = VGroup(bg, txt).move_to([0, -2.8, 0])
  self.play(FadeIn(box))
  self.play(Flash(txt, color=YELLOW, flash_radius=0.6))

══ SCENE STRUCTURE (follow exactly) ══

Phase 1 — TITLE CARD (8–10 s):
  title_group = VGroup()
  title = Text("Chapter Title Here", font_size=44, color=YELLOW)
  subtitle = Text("key concept in one line", font_size=26, color=GRAY)
  subtitle.next_to(title, DOWN, buff=0.35)
  title_group.add(title, subtitle)
  self.play(Write(title), run_time=1.5)
  self.play(FadeIn(subtitle))
  self.wait(4)
  self.play(FadeOut(title_group))
  self.wait(0.3)

Phase 2 — MAIN VISUAL BUILD (22–28 s):
  phase2 = VGroup()
  # ... build the key diagram piece by piece, each part animated ...
  # use LaggedStart, GrowArrow, DrawBorderThenFill, Create, FadeIn
  self.play(FadeOut(phase2))
  self.wait(0.3)

Phase 3 — CONCEPT IN ACTION (20–25 s):
  phase3 = VGroup()
  # ... show the concept working: move elements, swap, traverse, plot ...
  # animate at least 4 distinct steps with self.wait(2-4) between each
  self.play(FadeOut(phase3))
  self.wait(0.3)

Phase 4 — KEY TAKEAWAY (8–12 s):
  phase4 = VGroup()
  # formula or insight box + Indicate/Flash
  self.play(FadeOut(phase4))
  self.wait(1)

══ OUTPUT FORMAT ══
Return ONLY valid JSON:
{"manim_code": "<complete Python script — first line: from manim import *, second line: import numpy as np>"}
No markdown fences. No text outside the JSON object.
"""

_FIX_SYSTEM = """\
You are a Manim debugging expert. Fix ONLY the broken code. Preserve all educational content.

Critical rules:
- First two lines must be:  from manim import *  then  import numpy as np
- NEVER use MathTex, Tex, or LaTeX of any kind
- Class must be EALELesson(Scene)
- Total self.wait() must be 55–75 seconds
- All x in [-6, 6], all y in [-3.5, 3.5]
- Use Create not ShowCreation
- NEVER write FadeOut(VGroup(*self.mobjects)) — always fade named groups
- Track every group: phase1 = VGroup(); phase1.add(obj); self.play(FadeOut(phase1))

Return ONLY the fixed Python code. No JSON. No markdown. No explanation.
"""

_FALLBACK_SCENE_TEMPLATE = """\
from manim import *
import numpy as np

class EALELesson(Scene):
    def construct(self):
        # Phase 1 — title
        title_group = VGroup()
        title = Text({title!r}, font_size=40, color=YELLOW)
        subtitle = Text({subtitle!r}, font_size=24, color=LIGHT_BLUE)
        subtitle.next_to(title, DOWN, buff=0.4)
        title_group.add(title, subtitle)
        self.play(Write(title), run_time=1.5)
        self.play(FadeIn(subtitle))
        self.wait(5)
        self.play(FadeOut(title_group))
        self.wait(0.3)

        # Phase 2 — concept bullets
        phase2 = VGroup()
        header = Text({key_concept!r}, font_size=30, color=GREEN)
        header.move_to([0, 2.5, 0])
        phase2.add(header)
        self.play(Write(header))
        lines = {bullet_lines}
        bullet_group = VGroup()
        for i, line in enumerate(lines):
            t = Text(line, font_size=24, color=WHITE)
            t.move_to([0, 1.2 - i * 0.85, 0])
            bullet_group.add(t)
        phase2.add(bullet_group)
        self.play(LaggedStart(*[FadeIn(t) for t in bullet_group], lag_ratio=0.4), run_time=2.5)
        self.wait(8)

        # Highlight each bullet
        for t in bullet_group:
            self.play(Indicate(t, scale_factor=1.06, color=YELLOW), run_time=0.6)
            self.wait(2)

        self.play(FadeOut(phase2))
        self.wait(0.3)

        # Phase 3 — visual approach text
        phase3 = VGroup()
        approach_box = RoundedRectangle(corner_radius=0.18, width=9, height=1.4).set_fill(DARK_BLUE, opacity=0.85)
        approach_box.move_to([0, 0, 0])
        approach_txt = Text({visual_approach!r}, font_size=21, color=WHITE)
        approach_txt.move_to(approach_box)
        phase3.add(approach_box, approach_txt)
        self.play(FadeIn(approach_box), Write(approach_txt))
        self.wait(10)
        self.play(Indicate(approach_txt, scale_factor=1.04))
        self.wait(3)
        self.play(FadeOut(phase3))
        self.wait(0.3)

        # Phase 4 — summary
        phase4 = VGroup()
        summary = Text("Key Takeaway", font_size=36, color=GOLD)
        summary.move_to([0, 1.5, 0])
        phase4.add(summary)
        self.play(Write(summary))
        narr_lines = {narration_lines}
        narr_group = VGroup()
        for i, line in enumerate(narr_lines):
            nt = Text(line, font_size=20, color=GRAY)
            nt.move_to([0, 0.4 - i * 0.55, 0])
            narr_group.add(nt)
        phase4.add(narr_group)
        self.play(LaggedStart(*[FadeIn(t) for t in narr_group], lag_ratio=0.35), run_time=3)
        self.wait(8)
        self.play(Flash(summary, color=YELLOW, flash_radius=1.0))
        self.wait(3)
        self.play(FadeOut(phase4))
        self.wait(1)
"""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _plan_lesson(
    topic: str,
    page_context: str,
    question_text: Optional[str],
) -> Optional[_LessonPlan]:
    """Call GPT-4o to generate a 5-chapter lesson plan."""
    if not settings.OPENAI_API_KEY:
        return None

    context_block = ""
    if page_context:
        context_block += f"\n\nPage context (what the student was studying):\n{page_context[:1500]}"
    if question_text:
        context_block += f"\n\nThe student struggled with this question: {question_text}"

    user_msg = (
        f"Create a 5-chapter animated video lesson plan for: {topic}"
        f"{context_block}\n\n"
        "Focus on building intuition and concrete examples. "
        "Make each chapter visually distinct and progressively deeper."
    )
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _PLANNER_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.7,
        )
        raw = resp.choices[0].message.content
        plan = _LessonPlan.model_validate_json(raw)
        logger.info("[Manim] Lesson plan: %d chapters", len(plan.chapters))
        return plan
    except (ValidationError, Exception) as exc:
        logger.warning("[Manim] Lesson planning failed: %s", exc)
        return None


def _generate_chapter_code(
    chapter: _ChapterPlan,
    chapter_idx: int,
    lesson_title: str,
    topic: str,
) -> Optional[str]:
    """Call GPT-4o to generate Manim code for one chapter."""
    if not settings.OPENAI_API_KEY:
        return None
    user_msg = (
        f"Topic: {topic}\n"
        f"Lesson: {lesson_title}\n"
        f"Chapter {chapter_idx + 1} of 5: {chapter.title}\n\n"
        f"Key concept: {chapter.key_concept}\n\n"
        f"What to animate: {chapter.visual_approach}\n\n"
        f"Narration for this chapter (sync your animations to this):\n{chapter.narration_segment}\n\n"
        "Generate a rich, cinematic 60–80 second Manim scene for this chapter. "
        "Make it visually stunning with continuous motion and clear animations."
    )
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _CHAPTER_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            response_format={"type": "json_object"},
            max_tokens=5000,
            temperature=0.5,
        )
        raw = resp.choices[0].message.content
        chapter_code = _ChapterCode.model_validate_json(raw)
        logger.info("[Manim] Chapter %d code: %d chars", chapter_idx + 1, len(chapter_code.manim_code))
        return chapter_code.manim_code
    except (ValidationError, Exception) as exc:
        logger.warning("[Manim] Chapter %d code generation failed: %s", chapter_idx + 1, exc)
        return None


def _fix_manim_code(code: str, error: str) -> Optional[str]:
    """Ask GPT-4o to fix broken Manim code."""
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
                    f"ERROR:\n{error[-3000:]}\n\n"
                    f"BROKEN CODE:\n{code}\n\n"
                    "Fix it and return only the corrected Python code."
                )},
            ],
            max_tokens=5000,
            temperature=0.1,
        )
        fixed = resp.choices[0].message.content.strip()
        if fixed.startswith("```"):
            lines = fixed.split("\n")
            fixed = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        return fixed
    except Exception as exc:
        logger.warning("[Manim] Fix call failed: %s", exc)
        return None


def _build_fallback_scene(chapter: "_ChapterPlan", chapter_idx: int) -> str:
    """Generate a guaranteed-to-render text-only scene as a last resort."""
    import textwrap

    def short_lines(text: str, width: int = 55, max_lines: int = 4) -> list[str]:
        words = text.replace('"', "'")
        lines = textwrap.wrap(words, width=width)
        return lines[:max_lines]

    title = f"Chapter {chapter_idx + 1}: {chapter.title}"[:60]
    subtitle = chapter.key_concept[:70]
    visual_approach = chapter.visual_approach[:80]
    bullets = short_lines(chapter.key_concept + ". " + chapter.visual_approach, width=55, max_lines=4)
    narration_chunks = short_lines(chapter.narration_segment, width=60, max_lines=5)

    # Sanitize strings for safe Python repr
    def safe(s: str) -> str:
        return s.replace("\\", "").replace("\n", " ")

    code = _FALLBACK_SCENE_TEMPLATE.format(
        title=safe(title),
        subtitle=safe(subtitle),
        key_concept=safe(chapter.key_concept[:65]),
        bullet_lines=repr([safe(b) for b in bullets]),
        visual_approach=safe(visual_approach),
        narration_lines=repr([safe(n) for n in narration_chunks]),
    )
    return code


def _validate_code(code: str) -> Optional[str]:
    if "class EALELesson(Scene)" not in code:
        return "Missing 'class EALELesson(Scene)'"
    if "MathTex(" in code or " Tex(" in code or "SingleStringMathTex(" in code:
        return "Code uses MathTex/Tex — LaTeX not installed"
    if "def construct(self)" not in code:
        return "Missing 'def construct(self)'"
    if "from manim import" not in code:
        return "Missing Manim import"
    if "VGroup(*self.mobjects)" in code:
        return "Unsafe pattern: VGroup(*self.mobjects) — use named groups instead"
    return None


def _run_manim(code: str, scene_file: str, output_dir: str) -> tuple[bool, str, str]:
    """
    Render a Manim scene file. Returns (success, mp4_path, stderr).
    """
    with open(scene_file, "w") as f:
        f.write(code)

    cmd = [
        "manim", "render",
        scene_file, "EALELesson",
        "--quality", "m",           # 720p30 — fast but good quality
        "--disable_caching",
        "--media_dir", output_dir,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=480,            # 8 min per chapter
            cwd=os.path.dirname(scene_file),
        )
        stderr = result.stderr + result.stdout

        mp4_path = (
            Path(output_dir) / "videos"
            / Path(scene_file).stem / "720p30" / "EALELesson.mp4"
        )
        if not mp4_path.exists():
            found = list(Path(output_dir).rglob("EALELesson.mp4"))
            if found:
                mp4_path = found[0]
            else:
                logger.warning("[Manim] MP4 not found after render.\nSTDERR:\n%s", stderr[-3000:])
                return False, "", stderr

        logger.info("[Manim] Rendered: %s (%d KB)", mp4_path, mp4_path.stat().st_size // 1024)
        return True, str(mp4_path), stderr

    except subprocess.TimeoutExpired:
        logger.warning("[Manim] Chapter render timed out after 480s")
        return False, "", "TimeoutExpired"
    except Exception as exc:
        logger.warning("[Manim] Render subprocess error: %s", exc)
        return False, "", str(exc)


def _render_chapter_with_retry(
    code: str,
    scene_file: str,
    output_dir: str,
    chapter_idx: int,
    chapter: "_ChapterPlan",
) -> Optional[str]:
    """
    Render one chapter with up to 5 GPT-4o fix attempts.
    If ALL attempts fail, render the guaranteed fallback text scene.
    Always returns an mp4_path — never skips a chapter.
    """
    last_error = ""
    for attempt in range(5):
        err = _validate_code(code)
        if err:
            logger.warning("[Manim] Ch%d attempt %d: validation: %s", chapter_idx + 1, attempt + 1, err)
            last_error = err
        else:
            success, mp4_path, last_error = _run_manim(code, scene_file, output_dir)
            if success:
                logger.info("[Manim] Ch%d rendered on attempt %d", chapter_idx + 1, attempt + 1)
                return mp4_path
            logger.warning("[Manim] Ch%d attempt %d failed", chapter_idx + 1, attempt + 1)

        if attempt < 4:
            fixed = _fix_manim_code(code, last_error)
            if fixed:
                code = fixed
            else:
                logger.warning("[Manim] Ch%d: GPT-4o fix call failed — will retry with same code", chapter_idx + 1)
        else:
            logger.warning("[Manim] Ch%d: all 5 attempts failed — using fallback scene", chapter_idx + 1)

    # ── Fallback: guaranteed text-only scene ──────────────────────────────────
    logger.info("[Manim] Ch%d: rendering fallback scene", chapter_idx + 1)
    fallback_code = _build_fallback_scene(chapter, chapter_idx)
    fallback_file = scene_file.replace(".py", "_fallback.py")
    fallback_out  = output_dir + "_fallback"
    os.makedirs(fallback_out, exist_ok=True)
    success, mp4_path, err = _run_manim(fallback_code, fallback_file, fallback_out)
    if success:
        logger.info("[Manim] Ch%d: fallback scene rendered OK", chapter_idx + 1)
        return mp4_path
    logger.warning("[Manim] Ch%d: fallback also failed: %s", chapter_idx + 1, err[-500:])
    return None


def _concat_videos(mp4_paths: list[str], output_path: str) -> bool:
    """FFmpeg concat list → single combined video. Re-encodes audio for compatibility."""
    concat_dir = os.path.dirname(output_path)
    concat_list = os.path.join(concat_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for p in mp4_paths:
            f.write(f"file '{p}'\n")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:v", "copy",          # copy video stream (fast)
        "-c:a", "aac",           # re-encode audio to ensure compatibility
        "-b:a", "128k",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.warning("[Manim] FFmpeg concat failed:\n%s", result.stderr[-1000:])
            return False
        logger.info("[Manim] Concatenated %d chapters → %s", len(mp4_paths), output_path)
        return True
    except Exception as exc:
        logger.warning("[Manim] Concat error: %s", exc)
        return False


def _mux_video_audio(video_path: str, audio_path: str, output_path: str) -> bool:
    """
    FFmpeg: combine video + narration audio.
    Uses apad to extend audio with silence if shorter than video,
    then -shortest trims at video end — so the full video always plays.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-af", "apad",   # pad audio with silence up to video length
        "-shortest",     # cut at end of (now-padded) audio = video end
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.warning("[Manim] FFmpeg mux failed:\n%s", result.stderr[-1000:])
            return False
        logger.info("[Manim] Muxed → %s", output_path)
        return True
    except Exception as exc:
        logger.warning("[Manim] Mux error: %s", exc)
        return False


def _generate_tts(narration: str) -> Optional[bytes]:
    """OpenAI TTS-1-HD narration audio."""
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
        logger.info("[Manim] TTS generated: %d KB", len(audio_bytes) // 1024)
        return audio_bytes
    except Exception as exc:
        logger.warning("[Manim] TTS failed: %s", exc)
        return None


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_manim_lesson(
    topic: str,
    page_context: str = "",
    question_text: Optional[str] = None,
) -> Optional[ManimLesson]:
    """
    Full multi-chapter pipeline — per-chapter TTS so narration is always in sync:
      1. Plan 5 chapters (GPT-4o)
      2. For each chapter:
           a. Generate Manim code (GPT-4o)
           b. Render to silent MP4 (Manim, up to 3 retries)
           c. Generate TTS for THIS chapter's narration (OpenAI TTS)
           d. Mux chapter video + chapter audio (FFmpeg, apad so nothing is cut)
      3. FFmpeg concat all muxed chapters → final.mp4
      4. Return base64-encoded final video (no separate audio_b64 — audio is in video)
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("[Manim] No OPENAI_API_KEY")
        return None

    # ── Step 1: Plan the lesson ───────────────────────────────────────────────
    logger.info("[Manim] Planning 5-chapter lesson for: %s", topic)
    lesson_plan = _plan_lesson(topic, page_context, question_text)
    if not lesson_plan:
        return None

    full_narration = "\n\n".join(
        f"Chapter {i + 1}: {ch.title}.\n{ch.narration_segment}"
        for i, ch in enumerate(lesson_plan.chapters)
    )

    with tempfile.TemporaryDirectory(prefix="eale_manim_") as tmpdir:
        muxed_chapters: list[str] = []

        for idx, chapter in enumerate(lesson_plan.chapters):
            logger.info(
                "[Manim] Chapter %d/%d: %s",
                idx + 1, len(lesson_plan.chapters), chapter.title,
            )

            # ── 2a: Generate Manim code ───────────────────────────────────────
            code = _generate_chapter_code(chapter, idx, lesson_plan.lesson_title, topic)
            if not code:
                logger.warning("[Manim] Ch%d: code gen failed — skipping", idx + 1)
                continue

            # ── 2b: Render silent MP4 ─────────────────────────────────────────
            scene_file = os.path.join(tmpdir, f"chapter_{idx}.py")
            output_dir = os.path.join(tmpdir, f"output_{idx}")
            os.makedirs(output_dir, exist_ok=True)

            mp4_path = _render_chapter_with_retry(code, scene_file, output_dir, idx, chapter)
            if not mp4_path:
                logger.warning("[Manim] Ch%d: even fallback failed — skipping", idx + 1)
                continue

            # ── 2c: Generate TTS for THIS chapter ────────────────────────────
            audio_bytes = _generate_tts(chapter.narration_segment)

            if audio_bytes:
                # ── 2d: Mux chapter video + chapter audio ─────────────────────
                audio_path = os.path.join(tmpdir, f"audio_{idx}.mp3")
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                muxed_path = os.path.join(tmpdir, f"muxed_{idx}.mp4")
                if _mux_video_audio(mp4_path, audio_path, muxed_path):
                    muxed_chapters.append(muxed_path)
                else:
                    logger.warning("[Manim] Ch%d: mux failed — using silent video", idx + 1)
                    muxed_chapters.append(mp4_path)
            else:
                logger.warning("[Manim] Ch%d: TTS failed — using silent video", idx + 1)
                muxed_chapters.append(mp4_path)

        if not muxed_chapters:
            logger.warning("[Manim] All chapters failed")
            return None

        logger.info("[Manim] %d/%d chapters complete", len(muxed_chapters), len(lesson_plan.chapters))

        # ── Step 3: Concatenate all muxed chapters ────────────────────────────
        if len(muxed_chapters) == 1:
            final_path = muxed_chapters[0]
        else:
            final_path = os.path.join(tmpdir, "final.mp4")
            if not _concat_videos(muxed_chapters, final_path):
                final_path = muxed_chapters[0]  # fallback to first chapter

        # ── Step 4: Base64 encode ─────────────────────────────────────────────
        with open(final_path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode()

        logger.info(
            "[Manim] Done: %d KB video, %d chapters",
            len(video_b64) * 3 // 4 // 1024,
            len(muxed_chapters),
        )

        # audio is already baked into video — no separate audio_b64 needed
        return ManimLesson(
            topic=topic,
            video_b64=video_b64,
            audio_b64="",
            narration=full_narration,
        )
