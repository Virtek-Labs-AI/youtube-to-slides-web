import os
import uuid

import httpx
import structlog
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.db.models import Presentation, PresentationStatus
from app.services import presenton as presenton_service
from app.services import storage
from app.services.link_injector import inject_references
from app.services.pptx_renderer import render_pptx
from app.services.slide_generator import format_slides_as_markdown, generate_slides_from_transcript
from app.services.transcript import get_transcript

# Transient errors that warrant retrying the Presenton call before falling back.
_PRESENTON_TRANSIENT_ERRORS = (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError)

logger = structlog.get_logger(__name__)

celery_app = Celery("youtube_to_slides", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"

# Sync engine for Celery tasks (Celery workers are sync)
_sync_db_url = settings.database_url
if _sync_db_url.startswith("postgresql+asyncpg://"):
    _sync_db_url = _sync_db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
_sync_engine = create_engine(_sync_db_url, pool_pre_ping=True, pool_recycle=300)


@celery_app.task(name="generate_presentation")
def generate_presentation(presentation_id: int) -> None:
    with Session(_sync_engine) as db:
        presentation = db.get(Presentation, presentation_id)
        if not presentation:
            return

        presentation.status = PresentationStatus.processing
        db.commit()

        try:
            # Step 1: Get transcript
            transcript = get_transcript(presentation.video_id)

            # Step 2: Generate slide outline via LLM (content + YouTube URLs)
            slides_data = generate_slides_from_transcript(transcript, presentation.video_id)

            slides_list = slides_data.get("slides", [])
            if slides_list and slides_list[0].get("title"):
                presentation.title = slides_list[0]["title"]

            # Step 3: Render to PPTX
            filename = f"{presentation.video_id}_{uuid.uuid4().hex[:8]}.pptx"

            if settings.presenton_url:
                # Generate nicely styled PPTX with Presenton, then inject reference links.
                # Retries up to 3 times on transient errors; falls back to plain python-pptx
                # if Presenton remains unreachable after all attempts.
                try:
                    slides_markdown = format_slides_as_markdown(slides_data)
                    pptx_bytes = _generate_with_presenton(
                        slides_markdown, presentation.title or presentation.video_id
                    )
                    pptx_bytes = inject_references(pptx_bytes, slides_data)
                    pptx_path = _save_pptx_bytes(pptx_bytes, filename)
                except (*_PRESENTON_TRANSIENT_ERRORS, TimeoutError, RuntimeError) as presenton_exc:
                    logger.warning(
                        "presenton_unavailable_falling_back",
                        presentation_id=presentation_id,
                        exc_type=type(presenton_exc).__name__,
                        exc_msg=str(presenton_exc),
                        metric="presenton_fallback_total",
                    )
                    pptx_path = render_pptx(slides_data, filename)
            else:
                # Fallback: plain python-pptx renderer (dev without Presenton)
                pptx_path = render_pptx(slides_data, filename)

            if storage.is_s3_enabled():
                s3_key = f"presentations/{filename}"
                storage.upload_pptx(pptx_path, s3_key)
                try:
                    os.unlink(pptx_path)
                except OSError:
                    pass
                presentation.pptx_path = s3_key
            else:
                presentation.pptx_path = pptx_path

            presentation.status = PresentationStatus.done
            db.commit()

        except Exception as exc:
            presentation.status = PresentationStatus.failed
            logger.exception(
                "presentation_generation_failed",
                presentation_id=presentation_id,
                exc_type=type(exc).__name__,
            )
            presentation.error_message = (
                f"Generation failed ({type(exc).__name__}). Please try again."
            )
            db.commit()


@retry(
    retry=retry_if_exception_type(_PRESENTON_TRANSIENT_ERRORS),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=30),
    reraise=True,
)
def _generate_with_presenton(slides_markdown: list[str], title: str) -> bytes:
    """Call Presenton with up to 5 retry attempts on transient connection/HTTP errors.

    The aggressive backoff (5s → 10s → 20s → 30s) is intentional: Presenton is
    deployed as a serverless service and may need up to ~30s to cold-start before
    accepting connections.
    """
    return presenton_service.generate_pptx(slides_markdown, title)


def _save_pptx_bytes(pptx_bytes: bytes, filename: str) -> str:
    """Write PPTX bytes to the local storage directory and return the path."""
    storage_dir = settings.storage_path
    os.makedirs(storage_dir, exist_ok=True)
    filepath = os.path.join(storage_dir, filename)
    with open(filepath, "wb") as f:
        f.write(pptx_bytes)
    return filepath
