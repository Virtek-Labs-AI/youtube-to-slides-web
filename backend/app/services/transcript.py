import re
from dataclasses import dataclass

from youtube_transcript_api import YouTubeTranscriptApi


@dataclass
class TranscriptSegment:
    text: str
    start: float
    duration: float
    url: str


# Patterns for extracting video ID from various YouTube URL formats
_VIDEO_ID_PATTERNS = [
    # Standard watch URL: https://www.youtube.com/watch?v=VIDEO_ID
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})"),
    # Short URL: https://youtu.be/VIDEO_ID
    re.compile(r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})"),
    # Embed URL: https://www.youtube.com/embed/VIDEO_ID
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
    # Shorts URL: https://www.youtube.com/shorts/VIDEO_ID
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})"),
    # Live URL: https://www.youtube.com/live/VIDEO_ID
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})"),
    # Music URL: https://music.youtube.com/watch?v=VIDEO_ID
    re.compile(r"(?:https?://)?music\.youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})"),
    # Bare video ID (11 chars)
    re.compile(r"^([a-zA-Z0-9_-]{11})$"),
]


def extract_video_id(url: str) -> str | None:
    url = url.strip()
    for pattern in _VIDEO_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def get_transcript(video_id: str) -> list[dict]:
    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id)

    segments: list[dict] = []
    for entry in transcript:
        start = entry.start
        segments.append(
            {
                "text": entry.text,
                "start": start,
                "duration": entry.duration,
                "url": f"https://youtu.be/{video_id}?t={int(start)}",
            }
        )
    return segments
