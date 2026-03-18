"""Presenton self-hosted API client.

Calls a self-hosted Presenton instance to generate a styled PPTX.
Presenton handles all slide structuring, layout, and visual styling.
"""

import urllib.parse

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


def generate_pptx(slides_markdown: list[str], title: str) -> bytes:
    """Generate a styled PPTX via the self-hosted Presenton API.

    Uses the synchronous endpoint which blocks until generation is complete
    and returns the file path directly — no polling or internal Puppeteer
    PPTX model conversion step. Returns raw PPTX bytes.
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
            "export_as": "pptx",
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
    server_path: str = result["path"]
    logger.info("presenton_generation_complete", n_slides=n_slides, path=server_path)

    download_url = _build_download_url(base_url, server_path)
    logger.info("presenton_downloading_pptx", url=download_url)

    pptx_resp = httpx.get(download_url, timeout=60.0)
    pptx_resp.raise_for_status()
    return pptx_resp.content


def _build_download_url(base_url: str, server_path: str) -> str:
    """Construct the static download URL for a Presenton export file.

    Validates that the filename from the API response contains no path
    traversal sequences before embedding it in the URL.
    """
    if ".." in server_path or "\\" in server_path:
        raise ValueError(f"Presenton returned an invalid export path: {server_path!r}")
    filename = server_path.rsplit("/", 1)[-1]
    if not filename:
        raise ValueError(f"Presenton returned an invalid export path: {server_path!r}")
    url = f"{base_url}/app_data/exports/{urllib.parse.quote(filename)}"
    if not url.startswith(base_url):
        raise ValueError(f"Constructed download URL is outside the expected origin: {url!r}")
    return url
