from app.services.slide_generator import format_slides_as_markdown

SLIDES_DATA = {
    "slides": [
        {
            "type": "title",
            "title": "My Presentation",
            "bullets": [],
        },
        {
            "type": "content",
            "title": "Key Points",
            "bullets": [
                {"text": "Point with link", "url": "https://youtu.be/abc?t=30"},
                {"text": "Point without link"},
            ],
        },
        {
            "type": "takeaway",
            "title": "Takeaways",
            "bullets": [
                {"text": "Summary one"},
                "plain string bullet",
            ],
        },
    ]
}


class TestFormatSlidesAsMarkdown:
    def test_returns_one_string_per_slide(self) -> None:
        result = format_slides_as_markdown(SLIDES_DATA)
        assert len(result) == 3

    def test_slide_title_is_h1(self) -> None:
        result = format_slides_as_markdown(SLIDES_DATA)
        assert result[0].startswith("# My Presentation")

    def test_bullet_with_url_is_markdown_link(self) -> None:
        result = format_slides_as_markdown(SLIDES_DATA)
        assert "- [Point with link](https://youtu.be/abc?t=30)" in result[1]

    def test_bullet_without_url_is_plain_item(self) -> None:
        result = format_slides_as_markdown(SLIDES_DATA)
        assert "- Point without link" in result[1]

    def test_plain_string_bullet_rendered(self) -> None:
        result = format_slides_as_markdown(SLIDES_DATA)
        assert "- plain string bullet" in result[2]

    def test_empty_slides(self) -> None:
        assert format_slides_as_markdown({}) == []
        assert format_slides_as_markdown({"slides": []}) == []

    def test_slide_with_no_bullets(self) -> None:
        result = format_slides_as_markdown(SLIDES_DATA)
        # Title slide has no bullets — should still produce a markdown string
        assert result[0] == "# My Presentation"
