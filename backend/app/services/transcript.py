import math
import os
import re

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig


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

    When neither is set, returns None (library default).
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

    # No YouTube proxy configured.
    return None


def _has_punctuation(transcript) -> bool:
    """Check if the transcript has sentence-ending punctuation."""
    total = len(transcript)
    if total == 0:
        return False
    punctuated = sum(
        1 for entry in transcript if any(c in entry.text for c in ".?!")
    )
    return punctuated / total > 0.1


def _merge_into_sentences(video_id: str, transcript) -> list[dict]:
    """Merge short transcript fragments into full sentences using punctuation.

    YouTube transcripts come as 2-5 word fragments. This merges them into
    complete sentences, dramatically reducing segment count (5-10x) while
    preserving the timestamp of where each sentence begins.
    """
    sentences: list[dict] = []
    current_text = ""
    current_start: float | None = None
    current_duration = 0.0

    for entry in transcript:
        if current_start is None:
            current_start = entry.start

        text = entry.text
        if "." not in text:
            current_text += " " + text
            current_duration += entry.duration
            continue

        # Fragment contains sentence boundary — split on periods
        parts = text.split(".")
        durations = [len(p) / max(len(text), 1) * entry.duration for p in parts]

        for i, (part, dur) in enumerate(zip(parts, durations)):
            if i == 0:
                # Finish current sentence
                current_text += " " + part + "."
                current_duration += dur
                current_text = current_text.strip()
                if current_text and current_start is not None:
                    sentences.append({
                        "text": current_text,
                        "start": current_start,
                        "duration": current_duration,
                        "url": f"https://youtu.be/{video_id}?t={math.floor(current_start)}",
                    })
            elif part == "":
                continue
            else:
                # Start new sentence from mid-fragment boundary
                new_start = entry.start + durations[i - 1]
                if i < len(parts) - 1:
                    # Complete sentence within fragment
                    sentences.append({
                        "text": part.strip() + ".",
                        "start": new_start,
                        "duration": dur,
                        "url": f"https://youtu.be/{video_id}?t={math.floor(new_start)}",
                    })
                else:
                    # Last part — start of next sentence (incomplete)
                    current_text = part.strip()
                    current_start = new_start
                    current_duration = dur
                    continue

            # Reset for next sentence
            current_text = ""
            current_start = None
            current_duration = 0.0

        # If last part was empty (sentence ended with period), reset
        if parts[-1] == "":
            current_text = ""
            current_start = None
            current_duration = 0.0

    # Append any remaining incomplete sentence
    if current_text.strip() and current_start is not None:
        sentences.append({
            "text": current_text.strip(),
            "start": current_start,
            "duration": current_duration,
            "url": f"https://youtu.be/{video_id}?t={math.floor(current_start)}",
        })

    return sentences


def get_transcript(video_id: str) -> list[dict]:
    proxy_config = _get_proxy_config()
    ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
    transcript = ytt_api.fetch(video_id)

    if _has_punctuation(transcript):
        return _merge_into_sentences(video_id, transcript)

    # Fallback: no punctuation, return raw segments
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
