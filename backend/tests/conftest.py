"""Pytest configuration: set required env vars before any app module imports.

Settings() is instantiated at module level in app.core.config. Without these
dummy values, importing any module that depends on settings fails during
pytest collection with a pydantic ValidationError.
"""

import os

os.environ.setdefault("SECRET_KEY", "ci-test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///ci-test.db")
os.environ.setdefault("OPENAI_API_KEY", "ci-test-openai-key")
os.environ.setdefault("GOOGLE_CLIENT_ID", "ci-test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "ci-test-google-client-secret")
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", "ci-test-token-encryption-key")
