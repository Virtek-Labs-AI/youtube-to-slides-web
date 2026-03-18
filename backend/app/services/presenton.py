"""Presenton self-hosted API client.

Calls a self-hosted Presenton instance to generate a styled PPTX.
Presenton handles all slide structuring, layout, and visual styling.
"""

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


def generate_pptx(transcript: list[dict], n_slides: int = 10) -> bytes:
    """Generate a styled PPTX via the self-hosted Presenton API.

    Sends the raw transcript text to Presenton and lets it handle all slide
    structuring and layout. Returns the PPTX bytes.
    """
    base_url = settings.presenton_url.rstrip("/")  # type: ignore[union-attr]
    content = " ".join(seg["text"] for seg in transcript)

    resp = httpx.post(
        f"{base_url}/api/v1/ppt/presentation/generate",
        json={
            "content": content,
            "n_slides": n_slides,
            "export_as": "pptx",
            "theme": settings.presenton_template,
        },
        timeout=300.0,
    )
    if resp.is_error:
        logger.error(
            "presenton_api_error",
            status_code=resp.status_code,
            body=resp.text[:1000],
        )
    resp.raise_for_status()

    result = resp.json()
    download_path = result.get("path")
    if not download_path:
        raise RuntimeError(f"No download path in Presenton response: {result}")

    logger.info("presenton_generation_complete", n_slides=n_slides, path=download_path)

    download_url = f"{base_url}{download_path}" if download_path.startswith("/") else download_path
    pptx_resp = httpx.get(download_url, timeout=60.0)
    pptx_resp.raise_for_status()
    return pptx_resp.content
