from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    encrypt_token,
    exchange_code_for_tokens,
    generate_oauth_state,
    get_google_auth_url,
    get_google_user_info,
)
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

_COOKIE_SECURE = not settings.debug
_COOKIE_SAMESITE = "lax"
_STATE_COOKIE = "oauth_state"
_JWT_COOKIE = "access_token"


class AuthUrlResponse(BaseModel):
    url: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None = None

    model_config = {"from_attributes": True}


@router.get("/login", response_model=AuthUrlResponse)
async def login(response: Response):
    """Return Google OAuth URL and set a signed state cookie for CSRF protection."""
    state = generate_oauth_state()
    response.set_cookie(
        key=_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        max_age=600,  # 10 minutes — enough to complete the OAuth flow
    )
    return AuthUrlResponse(url=get_google_auth_url(state))


@router.get("/callback/google")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
    oauth_state: str | None = Cookie(default=None),
):
    """Handle Google OAuth callback. Validates CSRF state, sets httpOnly JWT cookie."""
    if not oauth_state or state != oauth_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state — possible CSRF attack",
        )

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

    # Encrypt tokens before storing in the database
    encrypted_access = encrypt_token(google_access_token)
    encrypted_refresh = encrypt_token(google_refresh_token) if google_refresh_token else None

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        user.name = user_info.get("name", user.name)
        user.picture = user_info.get("picture")
        user.google_access_token = encrypted_access
        if encrypted_refresh:
            user.google_refresh_token = encrypted_refresh
    else:
        user = User(
            email=email,
            name=user_info.get("name", email),
            picture=user_info.get("picture"),
            google_access_token=encrypted_access,
            google_refresh_token=encrypted_refresh,
        )
        db.add(user)

    await db.flush()

    jwt_token = create_access_token({"sub": str(user.id), "email": user.email})

    # Redirect to frontend — JWT is set as httpOnly cookie (not exposed to JS)
    redirect = RedirectResponse(url=f"{settings.frontend_url}/auth/callback", status_code=302)
    redirect.set_cookie(
        key=_JWT_COOKIE,
        value=jwt_token,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        max_age=86400,  # 24 hours, matches token expiry
    )
    redirect.delete_cookie(_STATE_COOKIE)
    return redirect


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(_JWT_COOKIE)
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user
