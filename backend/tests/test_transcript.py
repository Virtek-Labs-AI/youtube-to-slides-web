import pytest

from app.services.transcript import extract_video_id


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
def test_extract_video_id(url: str, expected: str | None):
    assert extract_video_id(url) == expected
