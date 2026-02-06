"""Configuration management with environment variables."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    """Return project root directory."""
    return Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # Google OAuth
    google_client_id: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(
        default=None, alias="GOOGLE_CLIENT_SECRET"
    )
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/callback",
        alias="GOOGLE_REDIRECT_URI",
    )

    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    timezone: str = Field(default="America/New_York", alias="TIMEZONE")

    # Backend
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")

    # Frontend
    streamlit_port: int = Field(default=8501, alias="STREAMLIT_PORT")

    # Vector database
    chroma_persist_dir: str = Field(
        default="data/embeddings", alias="CHROMA_PERSIST_DIR"
    )

    # Social media
    reddit_client_id: Optional[str] = Field(default=None, alias="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(
        default=None, alias="REDDIT_CLIENT_SECRET"
    )
    reddit_user_agent: Optional[str] = Field(
        default=None, alias="REDDIT_USER_AGENT"
    )
    twitter_bearer_token: Optional[str] = Field(
        default=None, alias="TWITTER_BEARER_TOKEN"
    )

    # Notification
    notification_email: Optional[str] = Field(
        default=None, alias="NOTIFICATION_EMAIL"
    )

    @property
    def project_root(self) -> Path:
        return _project_root()

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def embeddings_dir(self) -> Path:
        path = self.project_root / self.chroma_persist_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chat_history_dir(self) -> Path:
        return self.data_dir / "chat_history"

    @property
    def credentials_path(self) -> Path:
        return self.project_root / "config" / "credentials.json"

    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


def get_settings() -> Settings:
    """Return application settings singleton."""
    return Settings()
