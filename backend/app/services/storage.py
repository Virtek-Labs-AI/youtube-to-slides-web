"""Object storage service.

When S3_BUCKET is configured, PPTX files are stored in S3 (or any S3-compatible
provider like Cloudflare R2). This allows the Celery worker and API service to
share files even when running as separate Railway services with isolated filesystems.

When S3_BUCKET is not set, operations fall back to the local filesystem under
settings.storage_path (used in docker-compose dev with a shared named volume).
"""

import os
import tempfile
from contextlib import contextmanager
from typing import Generator

import boto3
from botocore.config import Config

from app.core.config import settings


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


def is_s3_enabled() -> bool:
    return bool(settings.s3_bucket)


def upload_pptx(local_path: str, key: str) -> None:
    """Upload a local PPTX file to S3 under the given key."""
    client = _s3_client()
    client.upload_file(
        local_path,
        settings.s3_bucket,
        key,
        ExtraArgs={"ContentType": "application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    )


def get_presigned_download_url(key: str, filename: str, expires_in: int = 3600) -> str:
    """Return a pre-signed URL that allows direct download of the PPTX from S3."""
    client = _s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ResponseContentDisposition": f'attachment; filename="{filename}"',
            "ResponseContentType": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        },
        ExpiresIn=expires_in,
    )


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
