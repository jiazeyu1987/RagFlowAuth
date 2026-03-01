from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Auth Backend - FastAPI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # AuthX JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES: int = 60 * 15  # 15 minutes
    JWT_REFRESH_TOKEN_EXPIRES: int = 60 * 60 * 24 * 7  # 7 days

    # Database
    DATABASE_PATH: str = "data/auth.db"

    # Diagnostics / debug logging
    PERMDBG_ENABLED: bool = False

    # File Upload
    UPLOAD_DIR: str = "data/uploads"
    PATENT_DOWNLOAD_DIR: str = "data/patent_downloads"
    MAX_FILE_SIZE: int = 16 * 1024 * 1024  # 16MB
    # Note: we intentionally do NOT accept legacy Office formats like .doc/.ppt/.pptx
    # to reduce preview/convert dependency complexity and user-facing failures.
    ALLOWED_EXTENSIONS: set = {
        ".txt",
        ".pdf",
        ".docx",
        ".md",
        ".xlsx",
        ".xls",
        ".csv",
        ".png",
        ".jpg",
        ".jpeg",
    }

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _coerce_debug_bool(cls, value):
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in {"1", "true", "yes", "on", "debug", "development", "dev"}:
            return True
        if text in {"0", "false", "no", "off", "release", "production", "prod"}:
            return False
        return value

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
