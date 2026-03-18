"""Object storage service.

When S3_BUCKET is configured, PPTX files are stored in S3 (or any S3-compatible
provider like Cloudflare R2). This allows the Celery worker and API service to
share files even when running as separate Railway services with isolated filesystems.

When S3_BUCKET is not set, operations fall back to the local filesystem under
settings.storage_path (used in docker-compose dev with a shared named volume).
"""

import os
import re
import tempfile
from contextlib import contextmanager
from typing import Generator

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from app.core.config import settings


def _s3_client() -> BaseClient:
    # Credentials and region are read from the standard AWS environment variables:
    # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION.
    # Only endpoint_url needs explicit wiring (for R2/MinIO; omit for AWS S3).
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        config=Config(signature_version="s3v4"),
    )


def is_s3_enabled() -> bool:
    return bool(settings.s3_bucket)


def safe_filename(filename: str) -> str:
    """Strip characters that would break a Content-Disposition header filename value."""
    return re.sub(r'["\\\r\n]', "_", filename)


def upload_pptx(local_path: str, key: str) -> None:
    """Upload a local PPTX file to S3 under the given key."""
    client = _s3_client()
    client.upload_file(
        local_path,
        settings.s3_bucket,
        key,
        ExtraArgs={
            "ContentType": (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
        },
    )


def stream_pptx(key: str) -> Generator[bytes, None, None]:
    """Stream S3 object bytes in chunks.

    Intended for use with FastAPI StreamingResponse so the file is proxied
    through the API rather than redirecting the client to S3. This avoids
    CORS issues when the frontend fetches with withCredentials=true and S3
    returns Access-Control-Allow-Origin: *.
    """
    client = _s3_client()
    response = client.get_object(Bucket=settings.s3_bucket, Key=key)
    body = response["Body"]
    try:
        while chunk := body.read(65536):
            yield chunk
    finally:
        body.close()


@contextmanager
def local_pptx_path(key: str) -> Generator[str, None, None]:
    """Context manager that downloads the PPTX from S3 to a temp file.

    Yields the local path and cleans up the temp file on exit.
    Intended for operations that need a local file path (e.g. Google Drive upload).
    """
    client = _s3_client()
    suffix = os.path.basename(key)
    with tempfile.NamedTemporaryFile(suffix=f"_{suffix}", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        client.download_file(settings.s3_bucket, key, tmp_path)
        yield tmp_path
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
