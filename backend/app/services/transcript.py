import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig


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


def _get_proxy_config() -> WebshareProxyConfig | GenericProxyConfig | None:
    """Build proxy config from YOUTUBE_PROXY_URL.

    If the URL contains credentials and points to webshare.io, uses
    WebshareProxyConfig for rotating residential IPs. Otherwise falls
    back to GenericProxyConfig.

    Expected format: http://user:pass@proxy.webshare.io:80
    """
    proxy_url = os.environ.get("YOUTUBE_PROXY_URL")
    if not proxy_url:
        return None
    parsed = urlparse(proxy_url)
    if parsed.username and parsed.password and "webshare" in (parsed.hostname or ""):
        return WebshareProxyConfig(
            proxy_username=parsed.username,
            proxy_password=parsed.password,
        )
    return GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)


def get_transcript(video_id: str) -> list[dict]:
    proxy_config = _get_proxy_config()
    ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
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
