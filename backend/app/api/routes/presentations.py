import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import decrypt_token
from app.db.models import Presentation, PresentationStatus, User
from app.db.session import get_db
from app.services.google_slides import import_to_google_slides
from app.services import storage
from app.services.transcript import extract_video_id
from app.tasks.presentation_tasks import generate_presentation

router = APIRouter(prefix="/api/presentations", tags=["presentations"])
limiter = Limiter(key_func=get_remote_address)


class CreatePresentationRequest(BaseModel):
    youtube_url: str

    @field_validator("youtube_url")
    @classmethod
    def validate_url_length(cls, v: str) -> str:
        if len(v) > 2048:
            raise ValueError("URL is too long")
        return v.strip()


class PresentationResponse(BaseModel):
    id: int
    youtube_url: str
    video_id: str
    title: str | None = None
    status: PresentationStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GoogleSlidesResponse(BaseModel):
    google_slides_url: str


@router.post("", response_model=PresentationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def create_presentation(
    request: Request,
    body: CreatePresentationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    video_id = extract_video_id(body.youtube_url)
    if not video_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YouTube URL",
        )

    presentation = Presentation(
        user_id=user.id,
        youtube_url=body.youtube_url,
        video_id=video_id,
        status=PresentationStatus.pending,
    )
    db.add(presentation)
    await db.flush()

    generate_presentation.delay(presentation.id)

    return presentation


@router.get("", response_model=list[PresentationResponse])
async def list_presentations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Presentation)
        .where(Presentation.user_id == user.id)
        .order_by(Presentation.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{presentation_id}", response_model=PresentationResponse)
async def get_presentation(
    presentation_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Presentation).where(
            Presentation.id == presentation_id,
            Presentation.user_id == user.id,
        )
    )
    presentation = result.scalar_one_or_none()
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    return presentation


@router.get("/{presentation_id}/download")
async def download_presentation(
    presentation_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Presentation).where(
            Presentation.id == presentation_id,
            Presentation.user_id == user.id,
        )
    )
    presentation = result.scalar_one_or_none()
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")

    if presentation.status != PresentationStatus.done or not presentation.pptx_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Presentation is not ready for download",
        )

    filename = f"{presentation.title or presentation.video_id}.pptx"

    if storage.is_s3_enabled():
        # Proxy the S3 object through the API rather than redirecting.
        # A redirect to a pre-signed URL fails when the frontend fetches with
        # withCredentials=true because S3 returns Access-Control-Allow-Origin: *,
        # which browsers block for credentialed requests.
        safe_filename = storage._safe_filename(filename)
        return StreamingResponse(
            storage.stream_pptx(presentation.pptx_path),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
        )

    # Local filesystem path (docker-compose dev with shared volume)
    # Path traversal guard — ensure the file is within the designated storage directory
    storage_root = os.path.realpath(settings.storage_path)
    resolved = os.path.realpath(presentation.pptx_path)
    if not resolved.startswith(storage_root + os.sep) and resolved != storage_root:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    path = Path(resolved)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Presentation file not found on server",
        )

    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )


@router.post("/{presentation_id}/import-google-slides", response_model=GoogleSlidesResponse)
async def import_google_slides_endpoint(
    presentation_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Presentation).where(
            Presentation.id == presentation_id,
            Presentation.user_id == user.id,
        )
    )
    presentation = result.scalar_one_or_none()
    if not presentation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")

    if presentation.status != PresentationStatus.done or not presentation.pptx_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Presentation is not ready",
        )

    if not user.google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account not linked. Please re-authenticate.",
        )

    try:
        access_token = decrypt_token(user.google_access_token)  # type: ignore[arg-type]
        refresh_token = (
            decrypt_token(user.google_refresh_token) if user.google_refresh_token else None
        )
        title = presentation.title or f"Slides - {presentation.video_id}"

        if storage.is_s3_enabled():
            # pptx_path is an S3 key — download to a temp file before uploading to Drive
            with storage.local_pptx_path(presentation.pptx_path) as local_path:
                url = import_to_google_slides(
                    pptx_path=local_path,
                    title=title,
                    access_token=access_token,
                    refresh_token=refresh_token,
                )
        else:
            url = import_to_google_slides(
                pptx_path=presentation.pptx_path,
                title=title,
                access_token=access_token,
                refresh_token=refresh_token,
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to import to Google Slides. Please try again.",
        )

    return GoogleSlidesResponse(google_slides_url=url)
