from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "YouTube to Slides"
    debug: bool = False
    secret_key: str
    frontend_url: str = "http://localhost:3000"

    # Daily presentation limit per user (0 = unlimited).
    # Future: override per-user via a tier/plan column on the User model.
    daily_presentation_limit: int = 5

    # Database
    database_url: str

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: str

    # Google OAuth
    google_client_id: str
    google_client_secret: str
    # BFF pattern: Google redirects to the Next.js frontend proxy, not FastAPI directly.
    google_redirect_uri: str = "http://localhost:3000/api/auth/callback/google"

    # Token encryption key (Fernet symmetric encryption).
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    token_encryption_key: str

    # Storage (local fallback for docker-compose dev)
    storage_path: str = "/tmp/youtube-to-slides"

    # S3-compatible object storage (AWS S3, Cloudflare R2, etc.)
    # When s3_bucket is set, PPTX files are stored in S3 instead of local disk.
    # Required for Railway deployments where API and Celery run as separate services.
    s3_bucket: str | None = None
    # Set for Cloudflare R2 / MinIO; leave unset for AWS S3.
    # Credentials and region come from standard AWS env vars:
    # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION.
    s3_endpoint_url: str | None = None

    # Presenton self-hosted presentation generator (optional)
    # When set, the Celery worker calls Presenton to generate visually styled slides,
    # then injects YouTube reference links with python-pptx.
    # Use the internal service URL, e.g. http://presenton:5000 (docker-compose / Railway).
    # When unset, the plain python-pptx renderer is used as a fallback.
    presenton_url: str | None = None
    # Template for Presenton slides. Built-in options: general, modern, standard, swift.
    # Defaults to "modern". Override via PRESENTON_TEMPLATE env var.
    # Note: Pexels image support is configured on the Presenton server via
    # IMAGE_PROVIDER=pexels and PEXELS_API_KEY env vars — not a per-request setting.
    presenton_template: str = "light"


settings = Settings()  # type: ignore[call-arg]
