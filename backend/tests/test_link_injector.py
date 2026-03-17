import io

import pytest
from pptx import Presentation
from pptx.util import Inches

from app.services.link_injector import _collect_refs, _timestamp_label, inject_references


def _minimal_pptx() -> bytes:
    """Build a minimal valid PPTX with one blank slide."""
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[6])
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


SLIDES_DATA = {
    "slides": [
        {
            "type": "title",
            "title": "My Video",
            "bullets": [],
        },
        {
            "type": "content",
            "title": "Topic A",
            "bullets": [
                {"text": "First point", "url": "https://youtu.be/abc123?t=60"},
                {"text": "Second point", "url": "https://youtu.be/abc123?t=120"},
            ],
        },
        {
            "type": "content",
            "title": "Topic B",
            "bullets": [
                {"text": "No url point"},
                {"text": "Linked point", "url": "https://youtu.be/abc123?t=300"},
            ],
        },
    ]
}


class TestTimestampLabel:
    def test_standard_t_param(self) -> None:
        assert _timestamp_label("https://youtu.be/abc?t=90") == "(1:30)"

    def test_zero_seconds(self) -> None:
        assert _timestamp_label("https://youtu.be/abc?t=0") == "(0:00)"

    def test_hours(self) -> None:
        assert _timestamp_label("https://youtu.be/abc?t=3661") == "(61:01)"

    def test_no_t_param(self) -> None:
        assert _timestamp_label("https://youtu.be/abc") == ""

    def test_malformed_t_param(self) -> None:
        assert _timestamp_label("https://youtu.be/abc?t=notanint") == ""


class TestCollectRefs:
    def test_collects_only_bullets_with_urls(self) -> None:
        refs = _collect_refs(SLIDES_DATA)
        assert len(refs) == 3

    def test_ref_tuple_structure(self) -> None:
        refs = _collect_refs(SLIDES_DATA)
        slide_title, bullet_text, url = refs[0]
        assert slide_title == "Topic A"
        assert bullet_text == "First point"
        assert url == "https://youtu.be/abc123?t=60"

    def test_skips_non_dict_bullets(self) -> None:
        data = {"slides": [{"title": "X", "bullets": ["plain string"]}]}
        assert _collect_refs(data) == []

    def test_empty_slides(self) -> None:
        assert _collect_refs({}) == []
        assert _collect_refs({"slides": []}) == []


class TestInjectReferences:
    def test_adds_references_slide(self) -> None:
        original = _minimal_pptx()
        result = inject_references(original, SLIDES_DATA)
        prs = Presentation(io.BytesIO(result))
        assert len(prs.slides) == 2  # original blank + references

    def test_no_urls_returns_unchanged(self) -> None:
        data = {"slides": [{"title": "X", "bullets": [{"text": "no url"}]}]}
        original = _minimal_pptx()
        result = inject_references(original, data)
        prs = Presentation(io.BytesIO(result))
        assert len(prs.slides) == 1

    def test_references_slide_has_title_text(self) -> None:
        original = _minimal_pptx()
        result = inject_references(original, SLIDES_DATA)
        prs = Presentation(io.BytesIO(result))
        last_slide = prs.slides[-1]
        texts = [shape.text_frame.text for shape in last_slide.shapes if shape.has_text_frame]
        assert any("Video References" in t for t in texts)

    def test_returns_bytes(self) -> None:
        original = _minimal_pptx()
        result = inject_references(original, SLIDES_DATA)
        assert isinstance(result, bytes)
        assert len(result) > 0
