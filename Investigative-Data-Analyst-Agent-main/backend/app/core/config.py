import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    Uses pydantic-settings to validate types and structures.
    """
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "Investigative Data Analyst Agent"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api"

    # Database Settings
    DATABASE_URL: str = "sqlite:///./idaa.db"

    # LLM Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Log Settings
    LOG_LEVEL: str = "INFO"


# Global settings instance
settings = Settings()
