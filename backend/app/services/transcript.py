import os
import re
from dataclasses import dataclass

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


def _get_proxy_config() -> WebshareProxyConfig | GenericProxyConfig:
    """Build proxy config from environment variables.

    Two modes:
    - Webshare residential (rotating): set YOUTUBE_WEBSHARE_USERNAME and
      YOUTUBE_WEBSHARE_PASSWORD. Uses WebshareProxyConfig which connects to
      Webshare's own rotating residential infrastructure.
    - Generic proxy (Decodo, etc.): set YOUTUBE_PROXY_URL as a full proxy URL
      including credentials, e.g. http://user:pass@gate.decodo.com:10000.
      Uses GenericProxyConfig which passes credentials via standard HTTP proxy
      auth.

    YOUTUBE_WEBSHARE_USERNAME takes precedence if both are set.

    When neither is set, returns an explicit no-proxy config (empty URL strings).
    This prevents the underlying requests session from inheriting system proxy
    env vars (e.g. Railway's HTTPS_PROXY for internal service routing), which
    would cause a ProxyError when trying to reach external YouTube URLs.
    """
    webshare_user = os.environ.get("YOUTUBE_WEBSHARE_USERNAME")
    webshare_pass = os.environ.get("YOUTUBE_WEBSHARE_PASSWORD")
    if webshare_user and webshare_pass:
        return WebshareProxyConfig(
            proxy_username=webshare_user,
            proxy_password=webshare_pass,
        )

    proxy_url = os.environ.get("YOUTUBE_PROXY_URL")
    if proxy_url:
        return GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)

    # No YouTube proxy configured. Explicitly disable proxy to prevent requests
    # from routing YouTube traffic through any system proxy env vars.
    return GenericProxyConfig(http_url="", https_url="")


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
