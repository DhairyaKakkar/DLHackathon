"""
YouTube transcript fetching for EALE context enrichment.

When a student is watching a YouTube video and triggers Learn It or a quiz,
the backend fetches the actual spoken transcript (captions) from YouTube and
passes it as rich context to GPT-4o — so the generated animation / question
is based on the video's real content, not just the page title.

No API key required. Falls back silently if transcript is unavailable.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Default cap for lightweight contexts such as question generation
_DEFAULT_TRANSCRIPT_CHARS = 4000


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from any common YouTube URL format."""
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_youtube_transcript(url: str, max_chars: int | None = _DEFAULT_TRANSCRIPT_CHARS) -> Optional[str]:
    """
    Fetch transcript for a YouTube video URL.

    Returns the transcript as a single string, optionally truncated,
    or None if the video has no captions or the fetch fails.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()

        # Try fetching English transcript; fall back to any available language
        try:
            fetched = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        except Exception:
            fetched = api.fetch(video_id)

        # v1.x returns FetchedTranscript — iterate for snippet objects with .text
        full_text = " ".join(
            (s.text if hasattr(s, "text") else s.get("text", ""))
            for s in fetched
        )

        if max_chars is not None and max_chars > 0:
            transcript = full_text[:max_chars]
            if len(full_text) > max_chars:
                transcript += "…"
        else:
            transcript = full_text

        logger.info(
            "[YouTube] Transcript fetched: video_id=%s chars=%d",
            video_id, len(transcript),
        )
        return transcript

    except Exception as exc:
        # TranscriptsDisabled, VideoUnavailable, network errors — all silent
        logger.info("[YouTube] Transcript unavailable for %s: %s", video_id, exc)
        return None
