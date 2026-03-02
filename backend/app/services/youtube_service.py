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

# Max characters to pass to GPT-4o (keeps prompt cost reasonable)
_MAX_TRANSCRIPT_CHARS = 4000


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


def get_youtube_transcript(url: str) -> Optional[str]:
    """
    Fetch transcript for a YouTube video URL.

    Returns the transcript as a single string (first ~4000 chars),
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

        # Truncate to keep prompt cost manageable
        truncated = full_text[:_MAX_TRANSCRIPT_CHARS]
        if len(full_text) > _MAX_TRANSCRIPT_CHARS:
            truncated += "…"

        logger.info(
            "[YouTube] Transcript fetched: video_id=%s chars=%d",
            video_id, len(truncated),
        )
        return truncated

    except Exception as exc:
        # TranscriptsDisabled, VideoUnavailable, network errors — all silent
        logger.info("[YouTube] Transcript unavailable for %s: %s", video_id, exc)
        return None
