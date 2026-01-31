from __future__ import annotations

from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = TOOL_DIR / "scripts"

CONFIG_FILE = Path.home() / ".ragflowauth_tool_config.txt"

# Log file (same folder as the UI entrypoint)
LOG_FILE = TOOL_DIR / "tool_log.log"

# Fixed Windows share (no prompts, no configuration)
DEFAULT_WINDOWS_SHARE_HOST = "192.168.112.72"
DEFAULT_WINDOWS_SHARE_NAME = "backup"
DEFAULT_WINDOWS_SHARE_USERNAME = "BJB110"
DEFAULT_WINDOWS_SHARE_PASSWORD = "showgood87"

# Fixed replica paths on server
MOUNT_POINT = "/mnt/replica"
REPLICA_TARGET_DIR = "/mnt/replica/RagflowAuth"

# Environments
PROD_SERVER_IP = "172.30.30.57"
TEST_SERVER_IP = "172.30.30.58"
DEFAULT_SERVER_USER = "root"

