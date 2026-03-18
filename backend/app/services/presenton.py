"""Presenton self-hosted API client.

Calls a self-hosted Presenton instance to generate a styled PPTX.
Presenton handles all slide structuring, layout, and visual styling.
"""

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


def generate_pptx(slides_markdown: list[str], title: str) -> bytes:
    """Generate a styled PPTX via the self-hosted Presenton API.

    Step 1: POST /api/v1/ppt/presentation/generate (no export_as) to create the
    presentation and get back a presentation_id.  This step does NOT trigger
    Puppeteer / Chromium internally, so it works in Railway's sandbox.

    Step 2: GET /api/v1/ppt/presentation/export/pptx?presentationId=<id> which
    builds the PPTX from the structured shapes data — again no Puppeteer needed.
    Returns raw PPTX bytes.
    """
    base_url = settings.presenton_url.rstrip("/")  # type: ignore[union-attr]
    content = "\n\n".join(slides_markdown)
    n_slides = len(slides_markdown)

    resp = httpx.post(
        f"{base_url}/api/v1/ppt/presentation/generate",
        json={
            "content": content,
            "n_slides": n_slides,
            "template": settings.presenton_template,
            "tone": "professional",
            "verbosity": "standard",
            "include_title_slide": True,
        },
        timeout=300.0,  # blocks until generation complete; 5 min ceiling
    )
    if resp.is_error:
        logger.error(
            "presenton_api_error",
            status_code=resp.status_code,
            body=resp.text[:1000],
        )
    resp.raise_for_status()

    result = resp.json()
    presentation_id: str = result["presentation_id"]
    logger.info("presenton_generation_complete", n_slides=n_slides, presentation_id=presentation_id)

    export_url = f"{base_url}/api/v1/ppt/presentation/export/pptx"
    logger.info("presenton_exporting_pptx", url=export_url, presentation_id=presentation_id)

    pptx_resp = httpx.get(
        export_url,
        params={"presentationId": presentation_id},
        timeout=60.0,
    )
    pptx_resp.raise_for_status()
    return pptx_resp.content
