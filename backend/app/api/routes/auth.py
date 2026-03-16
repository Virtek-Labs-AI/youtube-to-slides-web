from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    exchange_code_for_tokens,
    get_google_auth_url,
    get_google_user_info,
)
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthUrlResponse(BaseModel):
    url: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None = None

    model_config = {"from_attributes": True}


@router.get("/login", response_model=AuthUrlResponse)
async def login():
    url = get_google_auth_url()
    return AuthUrlResponse(url=url)


@router.get("/callback/google", response_model=TokenResponse)
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    try:
        tokens = await exchange_code_for_tokens(code)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code",
        )

    google_access_token = tokens.get("access_token")
    google_refresh_token = tokens.get("refresh_token")

    if not google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No access token received from Google",
        )

    try:
        user_info = await get_google_user_info(google_access_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch user info from Google",
        )

    email = user_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email in Google user info",
        )

    # Find or create user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        user.name = user_info.get("name", user.name)
        user.picture = user_info.get("picture")
        user.google_access_token = google_access_token
        if google_refresh_token:
            user.google_refresh_token = google_refresh_token
    else:
        user = User(
            email=email,
            name=user_info.get("name", email),
            picture=user_info.get("picture"),
            google_access_token=google_access_token,
            google_refresh_token=google_refresh_token,
        )
        db.add(user)

    await db.flush()

    jwt_token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=jwt_token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user
