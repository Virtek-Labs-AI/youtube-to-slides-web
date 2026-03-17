"""Presenton self-hosted API client.

Calls a self-hosted Presenton instance to generate a styled PPTX from
pre-structured slide markdown. Presenton handles template selection, layout,
and visual styling; our pipeline supplies the content structure.
"""

import time
import urllib.parse

import httpx

from app.core.config import settings


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
            "template": "general",
            "tone": "professional",
            "verbosity": "standard",
            "export_as": "pptx",
            "include_title_slide": False,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    task_id = resp.json()["id"]

    # Poll until complete (up to 10 minutes)
    for _ in range(120):
        time.sleep(5)
        status_resp = httpx.get(
            f"{base_url}/api/v1/ppt/presentation/status/{task_id}",
            timeout=15.0,
        )
        status_resp.raise_for_status()
        status = status_resp.json()
        if status["status"] == "completed":
            server_path = status["data"]["path"]
            break
        if status["status"] == "error":
            raise RuntimeError(f"Presenton generation failed: {status.get('error')}")
    else:
        raise TimeoutError("Presenton generation timed out after 10 minutes")

    # nginx serves /app_data/exports/ statically — construct download URL
    filename = server_path.rsplit("/", 1)[-1]
    download_url = f"{base_url}/app_data/exports/{urllib.parse.quote(filename)}"
    pptx_resp = httpx.get(download_url, timeout=60.0)
    pptx_resp.raise_for_status()
    return pptx_resp.content
