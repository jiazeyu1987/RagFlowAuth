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

# Fixed NAS backup paths
DEFAULT_NAS_HOST = "172.30.30.4"
DEFAULT_NAS_SHARE_NAME = "Backup"
DEFAULT_NAS_BACKUP_SUBDIR = "auth"
DEFAULT_NAS_USERNAME = "beifen"
DEFAULT_NAS_PASSWORD = "TYkHwI"
DEFAULT_NAS_SHARE_ROOT = Path(fr"\\{DEFAULT_NAS_HOST}\{DEFAULT_NAS_SHARE_NAME}")
DEFAULT_NAS_BACKUP_DIR = DEFAULT_NAS_SHARE_ROOT / DEFAULT_NAS_BACKUP_SUBDIR

NAS_MOUNT_POINT = "/mnt/nas"
NAS_BACKUP_TARGET_DIR = f"{NAS_MOUNT_POINT}/auth"
DEFAULT_LOCAL_BACKUP_DIR = DEFAULT_NAS_BACKUP_DIR
DEFAULT_LOCAL_BACKUP_DIR_TEXT = str(DEFAULT_LOCAL_BACKUP_DIR)

# Environments
PROD_SERVER_IP = "172.30.30.57"
TEST_SERVER_IP = "172.30.30.58"
DEFAULT_SERVER_USER = "root"

# RAGFlow base_url invariants (guardrails)
LOCAL_RAGFLOW_BASE_URL = "http://127.0.0.1:9380"
TEST_RAGFLOW_BASE_URL = f"http://{TEST_SERVER_IP}:9380"
PROD_RAGFLOW_BASE_URL = f"http://{PROD_SERVER_IP}:9380"
