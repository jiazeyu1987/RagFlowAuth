from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Literal


ExecFn = Callable[[str, int], tuple[bool, str]]
LogFn = Callable[[str], None]


StopMode = Literal["stop", "down"]


@dataclass(frozen=True)
class StopVerifyResult:
    ok: bool
    error: str = ""


class ServiceController:
    """
    Unified remote service stop/restart logic used by:
    - publish image / publish data
    - restore / sync data
    - manual "stop/restart" buttons

    Non-goals:
    - Manage unrelated containers (portainer/node-exporter) — we intentionally ignore them.
    """

    def __init__(self, *, exec_fn: ExecFn, log: LogFn | None = None) -> None:
        self._exec = exec_fn
        self._log = log

    def _log_line(self, msg: str) -> None:
        if not self._log:
            return
        try:
            self._log(msg)
        except Exception:
            pass

    @staticmethod
    def _compose_dir(app_dir: str) -> str:
        return f"{app_dir.rstrip('/')}/ragflow_compose"

    def _detect_compose(self, *, app_dir: str) -> str:
        compose_dir = self._compose_dir(app_dir)
        ok, out = self._exec(
            f"test -f {compose_dir}/docker-compose.yml && echo {compose_dir}/docker-compose.yml || "
            f"(test -f {compose_dir}/docker-compose.yaml && echo {compose_dir}/docker-compose.yaml || echo '')",
            20,
        )
        if not ok:
            return ""
        lines = (out or "").strip().splitlines()
        return lines[-1].strip() if lines else ""

    def stop_ragflowauth(self) -> None:
        self._exec("docker stop ragflowauth-backend ragflowauth-frontend 2>&1 || true", 300)

    def stop_ragflow_stack(self, *, app_dir: str, mode: StopMode) -> None:
        compose_dir = self._compose_dir(app_dir)
        compose_path = self._detect_compose(app_dir=app_dir)
        if compose_path:
            if mode == "down":
                self._exec(f"cd {compose_dir} 2>/dev/null && docker compose down 2>&1 || true", 900)
            else:
                self._exec(f"cd {compose_dir} 2>/dev/null && docker compose stop 2>&1 || true", 600)
        else:
            self._log_line("[STOP] compose file not found; falling back to docker stop by name/image")

        stop_prefix_cmd = r"""
set -e
names=$(docker ps -a --format '{{.Names}}' 2>/dev/null | grep '^ragflow_compose-' || true)
if [ -n "$names" ]; then
  docker stop $names 2>&1 || true
fi
""".strip()
        self._exec(stop_prefix_cmd, 600)

        stop_by_image_cmd = r"""
set -e
ids=$(
  (
    docker ps -q --filter ancestor=infiniflow/ragflow || true
    docker ps -q --filter ancestor=elasticsearch || true
    docker ps -q --filter ancestor=docker.elastic.co/elasticsearch/elasticsearch || true
    docker ps -q --filter ancestor=mysql || true
    docker ps -q --filter ancestor=valkey/valkey || true
    docker ps -q --filter ancestor=redis || true
    docker ps -q --filter ancestor=minio/minio || true
    docker ps -q --filter ancestor=quay.io/minio/minio || true
  ) | sort -u
)
if [ -n "$ids" ]; then
  docker stop $ids 2>&1 || true
fi
""".strip()
        self._exec(stop_by_image_cmd, 600)

    def verify_stopped(self, *, timeout_s: int = 60) -> StopVerifyResult:
        deadline = time.time() + max(1, int(timeout_s))
        while time.time() < deadline:
            check_cmd = r"""
set -e
echo RAGFLOWAUTH_STOP_CHECK >/dev/null
running_ids=$(
  (
    docker ps -q --filter "name=^ragflowauth-backend$" || true
    docker ps -q --filter "name=^ragflowauth-frontend$" || true
    docker ps -q --filter "name=^ragflow_compose-" || true
    docker ps -q --filter ancestor=infiniflow/ragflow || true
    docker ps -q --filter ancestor=elasticsearch || true
    docker ps -q --filter ancestor=docker.elastic.co/elasticsearch/elasticsearch || true
    docker ps -q --filter ancestor=mysql || true
    docker ps -q --filter ancestor=valkey/valkey || true
    docker ps -q --filter ancestor=redis || true
    docker ps -q --filter ancestor=minio/minio || true
    docker ps -q --filter ancestor=quay.io/minio/minio || true
  ) | sort -u
)
if [ -n "$running_ids" ]; then
  echo "RUNNING:"
  echo "$running_ids"
  exit 2
fi
echo "STOPPED"
""".strip()
            ok, out = self._exec(check_cmd, 60)
            text = (out or "").strip()
            if ok and text.endswith("STOPPED"):
                return StopVerifyResult(ok=True)
            time.sleep(3)

        ok, out = self._exec(
            "docker ps --no-trunc 2>&1 | "
            "grep -E '(ragflowauth-|ragflow_compose-|infiniflow/ragflow|elasticsearch|docker\\.elastic\\.co/elasticsearch/elasticsearch|mysql|valkey/valkey|redis|minio/minio|quay\\.io/minio/minio)' "
            "2>&1 || true",
            60,
        )
        diag = (out or "").strip() if ok else (out or "").strip()
        return StopVerifyResult(ok=False, error=diag or "containers may still be running; unable to verify clean stop")

    def stop_and_verify(
        self,
        *,
        app_dir: str,
        mode: StopMode,
        timeout_s: int = 60,
        who: str = "",
    ) -> StopVerifyResult:
        prefix = f"[{who}] " if who else ""
        self._log_line(f"{prefix}stopping ragflowauth containers")
        self.stop_ragflowauth()
        self._log_line(f"{prefix}stopping ragflow stack (mode={mode})")
        self.stop_ragflow_stack(app_dir=app_dir, mode=mode)
        self._log_line(f"{prefix}verifying containers are stopped (timeout {timeout_s}s)")
        res = self.verify_stopped(timeout_s=timeout_s)
        if res.ok:
            self._log_line(f"{prefix}containers stopped: OK")
        else:
            self._log_line(f"{prefix}[ERROR] containers still running or verify failed: {res.error}")
        return res

    def restart_best_effort(self, *, app_dir: str) -> None:
        compose_dir = self._compose_dir(app_dir)
        compose_path = self._detect_compose(app_dir=app_dir)
        if compose_path:
            self._exec(f"cd {compose_dir} 2>/dev/null && docker compose restart 2>&1 || true", 600)
            self._exec(f"cd {compose_dir} 2>/dev/null && docker compose up -d 2>&1 || true", 900)
        else:
            # Best-effort restart for name-prefix containers when compose is missing.
            self._exec(
                r"set -e; names=$(docker ps -a --format '{{.Names}}' 2>/dev/null | grep '^ragflow_compose-' || true); "
                r"[ -n \"$names\" ] && docker restart $names 2>&1 || true",
                600,
            )
        self._exec("docker restart ragflowauth-backend ragflowauth-frontend 2>&1 || true", 300)
