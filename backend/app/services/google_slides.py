from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.core.config import settings

GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _build_credentials(
    access_token: str, refresh_token: str | None = None
) -> Credentials:
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def list_drive_folders(
    access_token: str,
    refresh_token: str | None = None,
    parent_id: str = "root",
) -> list[dict]:
    """List folders inside a given parent folder on Google Drive."""
    creds = _build_credentials(access_token, refresh_token)
    service = build("drive", "v3", credentials=creds)

    query = (
        f"'{parent_id}' in parents"
        " and mimeType = 'application/vnd.google-apps.folder'"
        " and trashed = false"
    )
    results = (
        service.files()
        .list(q=query, fields="files(id,name)", orderBy="name", pageSize=100)
        .execute()
    )
    return results.get("files", [])


def import_to_google_slides(
    pptx_path: str,
    title: str,
    access_token: str,
    refresh_token: str | None = None,
    folder_id: str | None = None,
) -> str:
    """Upload a PPTX to Google Drive, converting it to Google Slides format.

    Automatically refreshes the access token if it has expired, provided a
    refresh_token and client credentials are available.
    """
    creds = _build_credentials(access_token, refresh_token)
    service = build("drive", "v3", credentials=creds)

    file_metadata: dict = {
        "name": title or "YouTube Slides",
        "mimeType": GOOGLE_SLIDES_MIME,
    }
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(pptx_path, mimetype=PPTX_MIME, resumable=True)

    created_file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id,webViewLink")
        .execute()
    )

    return created_file.get(
        "webViewLink",
        f"https://docs.google.com/presentation/d/{created_file['id']}",
    )
