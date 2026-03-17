"""Presenton self-hosted API client.

Calls a self-hosted Presenton instance to generate a styled PPTX from
pre-structured slide markdown. Presenton handles template selection, layout,
and visual styling; our pipeline supplies the content structure.
"""

import urllib.parse
from typing import Any

import httpx
import structlog
from tenacity import RetryError, retry, retry_if_exception_type, retry_if_result, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = structlog.get_logger(__name__)


def generate_pptx(slides_markdown: list[str], title: str) -> bytes:
    """Generate a styled PPTX via the self-hosted Presenton API.

    Passes pre-structured slide markdown so Presenton skips outline generation
    and renders directly using its template engine. Returns raw PPTX bytes.
    """
    base_url = settings.presenton_url.rstrip("/")  # type: ignore[union-attr]

    resp = httpx.post(
        f"{base_url}/api/v1/ppt/presentation/generate/async",
        json={
            "content": title,
            "slides_markdown": slides_markdown,
            "n_slides": len(slides_markdown),
            "template": "modern",
            "tone": "professional",
            "verbosity": "standard",
            "export_as": "pptx",
            "include_title_slide": True,
            **({"image_type": settings.presenton_image_type} if settings.presenton_image_type else {}),
        },
        timeout=60.0,  # generous for serverless cold-start wake-up
    )
    if resp.is_error:
        logger.error(
            "presenton_api_error",
            status_code=resp.status_code,
            body=resp.text[:1000],
        )
    resp.raise_for_status()
    task_id = resp.json()["id"]
    logger.info("presenton_task_submitted", task_id=task_id, n_slides=len(slides_markdown))

    try:
        result: dict[str, Any] = _poll_until_complete(base_url, task_id)
    except RetryError:
        raise TimeoutError("Presenton generation timed out after 10 minutes")

    server_path: str = result["path"]
    download_url = _build_download_url(base_url, server_path)
    logger.info("presenton_downloading_pptx", url=download_url)

    pptx_resp = httpx.get(download_url, timeout=60.0)
    pptx_resp.raise_for_status()
    return pptx_resp.content


@retry(
    wait=wait_exponential(multiplier=1, min=5, max=10),
    stop=stop_after_attempt(120),
    retry=retry_if_result(lambda result: result is None) | retry_if_exception_type(httpx.HTTPStatusError),
)
def _poll_until_complete(base_url: str, task_id: str) -> dict[str, Any] | None:
    """Poll the Presenton status endpoint until generation completes.

    Returns the completed task data dict, or None while still pending (causes
    tenacity to retry). Raises RuntimeError on error status.
    """
    resp = httpx.get(
        f"{base_url}/api/v1/ppt/presentation/status/{task_id}",
        timeout=15.0,
    )
    resp.raise_for_status()
    status = resp.json()
    if status["status"] == "completed":
        logger.info("presenton_task_completed", task_id=task_id)
        return status["data"]
    if status["status"] == "error":
        raise RuntimeError(f"Presenton generation failed: {status.get('error')}")
    logger.debug("presenton_task_pending", task_id=task_id, message=status.get("message"))
    return None


def _build_download_url(base_url: str, server_path: str) -> str:
    """Construct the static download URL for a Presenton export file.

    Validates that the filename from the API response contains no path
    traversal sequences before embedding it in the URL.
    """
    filename = server_path.rsplit("/", 1)[-1]
    if not filename or ".." in filename or "\\" in filename:
        raise ValueError(f"Presenton returned an invalid export path: {server_path!r}")
    url = f"{base_url}/app_data/exports/{urllib.parse.quote(filename)}"
    if not url.startswith(base_url):
        raise ValueError(f"Constructed download URL is outside the expected origin: {url!r}")
    return url
