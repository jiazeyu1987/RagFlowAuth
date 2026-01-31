from __future__ import annotations

from dataclasses import dataclass

from .environments import ENVIRONMENTS
from .constants import (
    CONFIG_FILE,
    DEFAULT_WINDOWS_SHARE_HOST,
    DEFAULT_WINDOWS_SHARE_NAME,
    DEFAULT_WINDOWS_SHARE_PASSWORD,
    DEFAULT_WINDOWS_SHARE_USERNAME,
)


@dataclass
class ServerConfig:
    ip: str = "172.30.30.57"
    user: str = "root"
    environment: str = "正式服务器"

    # Windows share mount config (fixed)
    windows_share_host: str = DEFAULT_WINDOWS_SHARE_HOST
    windows_share_name: str = DEFAULT_WINDOWS_SHARE_NAME
    windows_share_username: str = DEFAULT_WINDOWS_SHARE_USERNAME
    windows_share_password: str = DEFAULT_WINDOWS_SHARE_PASSWORD

    def __post_init__(self) -> None:
        self.load_config()
        # Hard override: do not allow config file to change these.
        self.windows_share_host = DEFAULT_WINDOWS_SHARE_HOST
        self.windows_share_name = DEFAULT_WINDOWS_SHARE_NAME
        self.windows_share_username = DEFAULT_WINDOWS_SHARE_USERNAME
        self.windows_share_password = DEFAULT_WINDOWS_SHARE_PASSWORD

    def load_config(self) -> None:
        if not CONFIG_FILE.exists():
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" not in line:
                        continue
                    key, value = line.strip().split("=", 1)
                    if key == "SERVER_IP":
                        self.ip = value
                    elif key == "SERVER_USER":
                        self.user = value
                    elif key == "ENVIRONMENT":
                        self.environment = value
        except Exception:
            # Best-effort: keep defaults on any parse error.
            return

    def save_config(self) -> None:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(f"SERVER_IP={self.ip}\n")
                f.write(f"SERVER_USER={self.user}\n")
                f.write(f"ENVIRONMENT={self.environment}\n")
                # Intentionally NOT persisting Windows share config (fixed values).
        except Exception:
            return

    def set_environment(self, env_name: str) -> bool:
        """Set a predefined environment (used by the UI dropdown)."""
        env = ENVIRONMENTS.get(env_name)
        if not env:
            return False
        self.ip = env.get("ip", self.ip)
        self.user = env.get("user", self.user)
        self.environment = env_name
        return True
