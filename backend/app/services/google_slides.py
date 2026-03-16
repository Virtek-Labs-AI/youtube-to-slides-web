from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.core.config import settings

GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def import_to_google_slides(
    pptx_path: str,
    title: str,
    access_token: str,
    refresh_token: str | None = None,
) -> str:
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )

    service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": title or "YouTube Slides",
        "mimeType": GOOGLE_SLIDES_MIME,
    }

    media = MediaFileUpload(pptx_path, mimetype=PPTX_MIME, resumable=True)

    created_file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id,webViewLink")
        .execute()
    )

    return created_file.get("webViewLink", f"https://docs.google.com/presentation/d/{created_file['id']}")
