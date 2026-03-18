import pytest
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

from app.services.transcript import _get_proxy_config, extract_video_id


@pytest.mark.parametrize(
    "url,expected",
    [
        # Standard watch URL
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # With extra params
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?list=PL123&v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # Short URL
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?t=30", "dQw4w9WgXcQ"),
        # Without https
        ("youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # Embed URL
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # Shorts URL
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # Live URL
        ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # Music URL
        ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # Bare video ID
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # With whitespace
        ("  https://youtu.be/dQw4w9WgXcQ  ", "dQw4w9WgXcQ"),
        # HTTP (not HTTPS)
        ("http://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        # Invalid URLs
        ("https://www.example.com/watch?v=dQw4w9WgXcQ", None),
        ("not-a-url", None),
        ("", None),
        ("https://www.youtube.com/watch", None),
        ("https://www.youtube.com/", None),
    ],
)
def test_extract_video_id(url: str, expected: str | None) -> None:
    assert extract_video_id(url) == expected


# ---------------------------------------------------------------------------
# _get_proxy_config
# ---------------------------------------------------------------------------


def test_proxy_config_no_env_vars_returns_none(monkeypatch) -> None:
    """No proxy env vars → None (library default)."""
    monkeypatch.delenv("YOUTUBE_WEBSHARE_USERNAME", raising=False)
    monkeypatch.delenv("YOUTUBE_WEBSHARE_PASSWORD", raising=False)
    monkeypatch.delenv("YOUTUBE_PROXY_URL", raising=False)

    config = _get_proxy_config()

    assert config is None


def test_proxy_config_youtube_proxy_url_returns_generic(monkeypatch) -> None:
    """YOUTUBE_PROXY_URL set → GenericProxyConfig with that URL for both http and https."""
    monkeypatch.delenv("YOUTUBE_WEBSHARE_USERNAME", raising=False)
    monkeypatch.delenv("YOUTUBE_WEBSHARE_PASSWORD", raising=False)
    monkeypatch.setenv("YOUTUBE_PROXY_URL", "http://user:pass@gate.decodo.com:10000")

    config = _get_proxy_config()

    assert isinstance(config, GenericProxyConfig)
    assert config.http_url == "http://user:pass@gate.decodo.com:10000"
    assert config.https_url == "http://user:pass@gate.decodo.com:10000"


def test_proxy_config_webshare_creds_returns_webshare(monkeypatch) -> None:
    """Webshare credentials set → WebshareProxyConfig (takes precedence over YOUTUBE_PROXY_URL)."""
    monkeypatch.setenv("YOUTUBE_WEBSHARE_USERNAME", "ws_user")
    monkeypatch.setenv("YOUTUBE_WEBSHARE_PASSWORD", "ws_pass")
    monkeypatch.setenv("YOUTUBE_PROXY_URL", "http://other:proxy@example.com:9999")

    config = _get_proxy_config()

    assert isinstance(config, WebshareProxyConfig)
