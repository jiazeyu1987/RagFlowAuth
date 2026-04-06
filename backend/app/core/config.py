from pydantic import field_validator
from pydantic_settings import BaseSettings


DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Auth Backend - FastAPI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    UVICORN_WORKERS: int = 1

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
    PAPER_DOWNLOAD_DIR: str = "data/paper_downloads"
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

    # Notification
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = ""
    SMTP_TO_EMAILS: str = ""
    DINGTALK_WEBHOOK_URL: str = ""
    NOTIFICATION_RETRY_INTERVAL_SECONDS: int = 60

    # CORS
    CORS_ORIGINS: list[str] = DEFAULT_CORS_ORIGINS.copy()

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
