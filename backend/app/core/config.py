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

    # Unified task scheduling quotas (WP-02)
    TASK_GLOBAL_CONCURRENCY_LIMIT: int = 2
    TASK_USER_CONCURRENCY_LIMIT: int = 1
    TASK_NAS_CONCURRENCY_LIMIT: int = 2
    TASK_BACKUP_CONCURRENCY_LIMIT: int = 1
    TASK_COLLECTION_CONCURRENCY_LIMIT: int = 2
    TASK_PAPER_DOWNLOAD_CONCURRENCY_LIMIT: int = 1
    TASK_PATENT_DOWNLOAD_CONCURRENCY_LIMIT: int = 1
    TASK_PAPER_PLAG_CONCURRENCY_LIMIT: int = 1
    TASK_UPLOAD_CONCURRENCY_LIMIT: int = 2

    # Task metric alerts (WP-02)
    TASK_ALERT_FAILURE_RATE_THRESHOLD: float = 0.3
    TASK_ALERT_BACKLOG_THRESHOLD: int = 20
    TASK_ALERT_AVG_DURATION_MS_THRESHOLD: int = 15 * 60 * 1000
    TASK_ALERT_LOG_COOLDOWN_SECONDS: int = 120
    TASK_METRICS_CACHE_TTL_MS: int = 800
    TASK_STATUS_CACHE_TTL_MS: int = 1500
    TASK_KIND_CACHE_TTL_SECONDS: int = 300

    # Egress mode runtime enforcement (WP-09)
    EGRESS_MODE_ENFORCEMENT_ENABLED: bool = True
    EGRESS_POLICY_CACHE_TTL_MS: int = 1000

    # ONLYOFFICE integration
    ONLYOFFICE_ENABLED: bool = False
    ONLYOFFICE_SERVER_URL: str = ""
    ONLYOFFICE_JWT_SECRET: str = ""
    ONLYOFFICE_PUBLIC_API_BASE_URL: str = ""
    ONLYOFFICE_FILE_TOKEN_TTL_SECONDS: int = 300
    ONLYOFFICE_FILE_TOKEN_SECRET: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    @field_validator("DEBUG", "EGRESS_MODE_ENFORCEMENT_ENABLED", mode="before")
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

    @field_validator(
        "TASK_GLOBAL_CONCURRENCY_LIMIT",
        "TASK_USER_CONCURRENCY_LIMIT",
        "TASK_NAS_CONCURRENCY_LIMIT",
        "TASK_BACKUP_CONCURRENCY_LIMIT",
        "TASK_COLLECTION_CONCURRENCY_LIMIT",
        "TASK_PAPER_DOWNLOAD_CONCURRENCY_LIMIT",
        "TASK_PATENT_DOWNLOAD_CONCURRENCY_LIMIT",
        "TASK_PAPER_PLAG_CONCURRENCY_LIMIT",
        "TASK_UPLOAD_CONCURRENCY_LIMIT",
        "TASK_ALERT_BACKLOG_THRESHOLD",
        "TASK_ALERT_AVG_DURATION_MS_THRESHOLD",
        "TASK_ALERT_LOG_COOLDOWN_SECONDS",
        "TASK_METRICS_CACHE_TTL_MS",
        "TASK_STATUS_CACHE_TTL_MS",
        "TASK_KIND_CACHE_TTL_SECONDS",
        "EGRESS_POLICY_CACHE_TTL_MS",
        mode="before",
    )
    @classmethod
    def _coerce_non_negative_int(cls, value):
        try:
            normalized = int(value)
        except Exception:
            return value
        return max(0, normalized)

    @field_validator("TASK_ALERT_FAILURE_RATE_THRESHOLD", mode="before")
    @classmethod
    def _coerce_failure_rate_threshold(cls, value):
        try:
            normalized = float(value)
        except Exception:
            return value
        return max(0.0, min(normalized, 1.0))

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
