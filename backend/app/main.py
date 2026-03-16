import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, presentations
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.storage_path, exist_ok=True)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(presentations.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
