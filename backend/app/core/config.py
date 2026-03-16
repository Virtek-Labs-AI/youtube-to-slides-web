from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "YouTube to Slides"
    debug: bool = False
    secret_key: str
    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: str

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Anthropic
    anthropic_api_key: str

    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/api/auth/callback/google"

    # Storage
    storage_path: str = "/tmp/youtube-to-slides"


settings = Settings()
