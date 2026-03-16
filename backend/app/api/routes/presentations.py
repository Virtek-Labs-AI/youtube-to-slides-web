from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import Presentation, PresentationStatus, User
from app.db.session import get_db
from app.services.google_slides import import_to_google_slides
from app.services.transcript import extract_video_id
from app.tasks.presentation_tasks import generate_presentation

router = APIRouter(prefix="/api/presentations", tags=["presentations"])


class CreatePresentationRequest(BaseModel):
    youtube_url: str


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
async def create_presentation(
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

    path = Path(presentation.pptx_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Presentation file not found on server",
        )

    filename = f"{presentation.title or presentation.video_id}.pptx"
    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )


@router.post("/{presentation_id}/import-google-slides", response_model=GoogleSlidesResponse)
async def import_google_slides(
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
        url = import_to_google_slides(
            pptx_path=presentation.pptx_path,
            title=presentation.title or f"Slides - {presentation.video_id}",
            access_token=user.google_access_token,
            refresh_token=user.google_refresh_token,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to import to Google Slides: {exc}",
        )

    return GoogleSlidesResponse(google_slides_url=url)
