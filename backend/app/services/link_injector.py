"""Inject YouTube reference links into a Presenton-generated PPTX.

Presenton produces beautifully styled slides but does not embed the per-bullet
YouTube timestamp URLs. This module appends a 'Video References' slide so
viewers can jump to the exact moment in the source video for each key point.
"""

import io
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt


def inject_references(pptx_bytes: bytes, slides_data: dict[str, Any]) -> bytes:
    """Append a 'Video References' slide to a Presenton-generated PPTX.

    Collects all (slide_title, bullet_text, url) tuples from slides_data
    and renders them as clickable hyperlinks on a new blank slide.
    Returns the modified PPTX as bytes.
    """
    refs = _collect_refs(slides_data)
    if not refs:
        return pptx_bytes

    prs = Presentation(io.BytesIO(pptx_bytes))

    blank_layout = prs.slide_layouts[6]  # Blank
    slide = prs.slides.add_slide(blank_layout)

    # Slide heading
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.6))
    tf = title_box.text_frame
    run = tf.paragraphs[0].add_run()
    run.text = "Video References"
    run.font.bold = True
    run.font.size = Pt(24)
    run.font.color.rgb = RGBColor(0x1F, 0x1F, 0x1F)

    # References body
    body_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.0), Inches(12.3), Inches(6.0))
    tf = body_box.text_frame
    tf.word_wrap = True

    first = True
    current_section: str | None = None
    for slide_title, bullet_text, url in refs:
        if slide_title != current_section:
            current_section = slide_title
            para = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            run = para.add_run()
            run.text = slide_title
            run.font.bold = True
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

        para = tf.add_paragraph()
        para.level = 1
        run = para.add_run()
        run.text = f"{bullet_text}  {_timestamp_label(url)}"
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x0D, 0x6E, 0xFD)
        run.hyperlink.address = url

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()


def _collect_refs(slides_data: dict[str, Any]) -> list[tuple[str, str, str]]:
    refs: list[tuple[str, str, str]] = []
    for slide in slides_data.get("slides", []):
        title = slide.get("title", "")
        for bullet in slide.get("bullets", []):
            if not isinstance(bullet, dict):
                continue
            url = bullet.get("url", "")
            if url:
                refs.append((title, bullet.get("text", ""), url))
    return refs


def _timestamp_label(url: str) -> str:
    if "?t=" in url:
        try:
            seconds = int(url.split("?t=")[1])
            minutes, secs = divmod(seconds, 60)
            return f"({minutes}:{secs:02d})"
        except (ValueError, IndexError):
            pass
    return ""
