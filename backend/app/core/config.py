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
    UVICORN_WORKERS: int = 2

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
    MAX_FILE_SIZE: int = 16 * 1024 * 1024  # deprecated: no longer enforced
    ALLOWED_EXTENSIONS: set = {
        ".txt",
        ".pdf",
        ".docx",
        ".md",
        ".xlsx",
        ".xls",
        ".ppt",
        ".pptx",
        ".csv",
        ".png",
        ".jpg",
        ".jpeg",
    }

    # ONLYOFFICE integration
    ONLYOFFICE_ENABLED: bool = False
    ONLYOFFICE_SERVER_URL: str = ""
    ONLYOFFICE_JWT_SECRET: str = ""
    ONLYOFFICE_PUBLIC_API_BASE_URL: str = ""
    ONLYOFFICE_FILE_TOKEN_TTL_SECONDS: int = 300
    ONLYOFFICE_FILE_TOKEN_SECRET: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Data security resilience switches
    BACKUP_SCHEDULER_ENABLED: bool = True
    DATA_SECURITY_SCAN_MOUNT_STATS: bool = False

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
