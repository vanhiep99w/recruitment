"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and .env file support.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:@localhost:5432/recruitment"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- LLM Proxy ---
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_API_VERSION: str | None = None          # For Azure OpenAI
    LLM_DEPLOYMENT_NAME: str | None = None      # For Azure OpenAI
    LLM_CHAT_MODEL: str = "gpt-4o-mini"
    LLM_EMBED_MODEL: str = "text-embedding-ada-002"

    # --- Authentication ---
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Application ---
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_azure(self) -> bool:
        """True when configured for Azure OpenAI endpoint."""
        return self.LLM_API_VERSION is not None


# Module-level singleton — import `settings` everywhere
settings = Settings()
