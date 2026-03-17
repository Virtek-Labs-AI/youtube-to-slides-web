import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import auth, presentations
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.storage_path, exist_ok=True)
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(auth.router)
app.include_router(presentations.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
