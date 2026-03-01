"""
Deterministic variant generator.

Each strategy receives a Question ORM object and returns a list of
(text, correct_answer, options, variant_template) tuples.

Optional LLM path (USE_LLM_VARIANTS=true + OPENAI_API_KEY set) calls
GPT to generate richer variants; falls back to deterministic on failure.
"""
import json
import re
import random
from typing import Optional
from sqlalchemy.orm import Session

from app.models import Question, QuestionType
from app.config import settings


# ─── Deterministic strategies ─────────────────────────────────────────────────

def _shuffle_options(options: list[str], correct: str) -> list[str]:
    """Return a shuffled copy of options, keeping correct answer present."""
    opts = list(options)
    random.shuffle(opts)
    return opts


def _rephrase_question(text: str) -> str:
    """Simple surface-level rephrasing rules."""
    rephrases = [
        (r"^What is ", "Which of the following describes "),
        (r"^Which ", "What "),
        (r"^What does ", "What is the result of "),
        (r"\?$", " in Python?"),
    ]
    new_text = text
    for pattern, replacement in rephrases:
        new_text, n = re.subn(pattern, replacement, new_text, count=1)
        if n:
            break
    if new_text == text:
        # fallback: prepend context
        new_text = "Consider the following — " + text[0].lower() + text[1:]
    return new_text


def _number_substitution(text: str, correct: str) -> tuple[str, str]:
    """Replace numbers in text + correct_answer with scaled equivalents."""
    nums = re.findall(r"\b\d+\b", text)
    if not nums:
        return text, correct

    target = nums[0]
    new_val = str(int(target) + 1)
    new_text = text.replace(target, new_val, 1)

    # Try to update the answer if it contains the same number
    new_answer = correct.replace(target, new_val, 1) if target in correct else correct
    return new_text, new_answer


def _generate_deterministic_variants(
    question: Question, num: int
) -> list[tuple[str, str, Optional[list[str]], str]]:
    """
    Returns up to `num` variant tuples:
        (text, correct_answer, options_or_None, template_tag)
    """
    variants = []

    # Strategy 1: rephrase
    if len(variants) < num:
        new_text = _rephrase_question(question.text)
        if new_text != question.text:
            opts = _shuffle_options(question.options, question.correct_answer) if question.options else None
            variants.append((new_text, question.correct_answer, opts, "rephrase"))

    # Strategy 2: number substitution (for numeric contexts)
    if len(variants) < num and question.question_type == QuestionType.MCQ:
        new_text, new_ans = _number_substitution(question.text, question.correct_answer)
        if new_text != question.text:
            # Build plausible wrong options from original options
            if question.options:
                wrong = [o for o in question.options if o != question.correct_answer][:3]
                new_opts = [new_ans] + wrong
                random.shuffle(new_opts)
            else:
                new_opts = None
            variants.append((new_text, new_ans, new_opts, "number_substitution"))

    # Strategy 3: context shift — wrap in a scenario
    if len(variants) < num:
        contexts = [
            "In a production Python codebase, ",
            "During a code review, a colleague asks: ",
            "A student learning Python wonders: ",
        ]
        ctx = contexts[len(variants) % len(contexts)]
        new_text = ctx + question.text[0].lower() + question.text[1:]
        opts = _shuffle_options(question.options, question.correct_answer) if question.options else None
        variants.append((new_text, question.correct_answer, opts, "context_shift"))

    return variants[:num]


# ─── Optional LLM path ────────────────────────────────────────────────────────

def _generate_llm_variants(
    question: Question, num: int
) -> list[tuple[str, str, Optional[list[str]], str]]:
    """Generate variants via OpenAI (requires OPENAI_API_KEY)."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        prompt = (
            f"Generate {num} distinct variant(s) of the following question. "
            "Each variant must test the SAME concept but use different wording, numbers, or context.\n\n"
            f"Original question: {question.text}\n"
            f"Correct answer: {question.correct_answer}\n"
            f"Question type: {question.question_type.value}\n"
        )
        if question.options:
            prompt += f"Options: {json.dumps(question.options)}\n"

        prompt += (
            "\nRespond ONLY with a JSON array of objects, each having: "
            '"text", "correct_answer", "options" (list or null), "template_tag" (string).'
        )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=800,
        )

        raw = json.loads(resp.choices[0].message.content)
        items = raw if isinstance(raw, list) else raw.get("variants", [])
        results = []
        for item in items[:num]:
            results.append(
                (
                    item["text"],
                    item["correct_answer"],
                    item.get("options"),
                    item.get("template_tag", "llm"),
                )
            )
        return results
    except Exception:
        # Fall back silently
        return _generate_deterministic_variants(question, num)


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_variants(
    db: Session, question: Question, num_variants: int = 2, use_llm: bool = False
) -> list[Question]:
    """
    Generate and persist `num_variants` Question variants for `question`.
    Returns the newly created variant Question objects.
    """
    if use_llm and settings.USE_LLM_VARIANTS and settings.OPENAI_API_KEY:
        raw_variants = _generate_llm_variants(question, num_variants)
    else:
        raw_variants = _generate_deterministic_variants(question, num_variants)

    created: list[Question] = []
    for text, correct, opts, template in raw_variants:
        variant = Question(
            topic_id=question.topic_id,
            text=text,
            question_type=question.question_type,
            difficulty=question.difficulty,
            correct_answer=correct,
            options=opts,
            is_variant=True,
            original_question_id=question.id,
            variant_template=template,
        )
        db.add(variant)
        created.append(variant)

    db.commit()
    for v in created:
        db.refresh(v)
    return created
