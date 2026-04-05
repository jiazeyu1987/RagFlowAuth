from __future__ import annotations

import json
import os
import time
import unittest
from dataclasses import dataclass

from tool.maintenance.core.constants import TEST_SERVER_IP
from tool.maintenance.core.ssh_executor import SSHExecutor


def _extract_json_marker(output: str) -> dict:
    marker = "__E2E_JSON__="
    for line in (output or "").splitlines()[::-1]:
        if line.startswith(marker):
            return json.loads(line[len(marker) :])
    raise AssertionError(f"missing marker {marker} in output:\n{output}")


@dataclass(frozen=True)
class BackupJobInfo:
    job_id: int
    output_dir: str
    kind: str


class TestE2EBackupRestoreDestructive(unittest.TestCase):
    """
    Destructive E2E:
    - Create canary user + canary dataset on TEST server
    - Run FULL backup
    - Delete both
    - Restore from backup pack (auth.db + ragflow volumes)
    - Verify both are restored

    Safety:
    - Hard-coded to TEST server only
    - Requires explicit opt-in env vars
    """

    @classmethod
    def setUpClass(cls) -> None:
        if os.environ.get("RAGFLOWAUTH_E2E_BACKUP_RESTORE", "0") != "1":
            raise unittest.SkipTest("Set RAGFLOWAUTH_E2E_BACKUP_RESTORE=1 to enable destructive E2E test")
        if os.environ.get("RAGFLOWAUTH_I_UNDERSTAND_DESTRUCTIVE", "") != "YES":
            raise unittest.SkipTest("Set RAGFLOWAUTH_I_UNDERSTAND_DESTRUCTIVE=YES to enable destructive E2E test")

    def setUp(self) -> None:
        # Must only ever target the test server.
        self.server_host = TEST_SERVER_IP
        self.server_user = "root"
        self.ssh = SSHExecutor(self.server_host, self.server_user)

        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        self.canary_username = f"e2e_restore_canary_{ts}"
        self.canary_password = "Aa123456"
        self.canary_dataset_name = f"e2e_restore_dataset_{ts}"

    def _ssh(self, command: str, *, timeout_s: int = 310) -> str:
        ok, out = self.ssh.execute(command, timeout_seconds=timeout_s)
        if not ok:
            raise AssertionError(f"SSH command failed:\ncmd={command}\n\nout=\n{out}")
        return out or ""

    def _docker_exec_backend_py(self, py_code: str, *, timeout_s: int = 310) -> dict:
        # Avoid Windows/local quoting issues by streaming python code via stdin.
        cmd = "docker exec -i ragflowauth-backend python -"
        ok, out = self.ssh.execute(cmd, timeout_seconds=timeout_s, stdin_data=(py_code.rstrip() + "\n"))
        if not ok:
            raise AssertionError(f"SSH command failed:\ncmd={cmd}\n\nout=\n{out}")
        return _extract_json_marker(out)

    def _ensure_backup_target_local(self) -> None:
        res = self._docker_exec_backend_py(
            """
from backend.services.data_security_store import DataSecurityStore
import json

store = DataSecurityStore()
s = store.get_settings()

target_mode = getattr(s, "target_mode", "")
target_local_dir = getattr(s, "target_local_dir", "")

print("__E2E_JSON__=" + json.dumps({"target_mode": target_mode, "target_local_dir": target_local_dir}, ensure_ascii=False))
""".strip()
        )
        if res.get("target_mode") != "local":
            raise unittest.SkipTest(
                f"Test server data_security_settings.target_mode must be 'local' for E2E. got={res.get('target_mode')}"
            )
        if not res.get("target_local_dir"):
            raise unittest.SkipTest("Test server data_security_settings.target_local_dir is empty")

    def _create_canary_user(self) -> dict:
        return self._docker_exec_backend_py(
            f"""
from backend.services.users.store import UserStore

store = UserStore()
u = store.create_user(username={self.canary_username!r}, password={self.canary_password!r}, role="viewer", created_by="e2e")
print("__E2E_JSON__=" + __import__("json").dumps({{"user_id": u.user_id, "username": u.username}}, ensure_ascii=False))
""".strip()
        )

    def _user_exists(self, username: str) -> bool:
        res = self._docker_exec_backend_py(
            f"""
import sqlite3

conn = sqlite3.connect("/app/data/auth.db")
try:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE username = ?", ({username!r},))
    n = int(cur.fetchone()[0] or 0)
finally:
    conn.close()

print("__E2E_JSON__=" + __import__("json").dumps({{"exists": n > 0, "count": n}}, ensure_ascii=False))
""".strip()
        )
        return bool(res.get("exists"))

    def _delete_user_by_username(self, username: str) -> None:
        self._docker_exec_backend_py(
            f"""
import sqlite3

conn = sqlite3.connect("/app/data/auth.db")
try:
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE username = ?", ({username!r},))
    conn.commit()
    deleted = cur.rowcount
finally:
    conn.close()

print("__E2E_JSON__=" + __import__("json").dumps({{"deleted": int(deleted)}}, ensure_ascii=False))
""".strip()
        )

    def _ragflow_create_dataset(self, name: str) -> dict:
        # Use RAGFlow HTTP API via RagflowService's configured client.
        return self._docker_exec_backend_py(
            f"""
from backend.services.ragflow_service import RagflowService
import json

svc = RagflowService()
payload = svc._http.post_json("/api/v1/datasets", body={{"name": {name!r}}}) or {{}}
data = payload.get("data")
dataset_id = None
if isinstance(data, dict):
    dataset_id = data.get("id") or data.get("dataset_id")
elif isinstance(data, list) and data:
    if isinstance(data[0], dict):
        dataset_id = data[0].get("id") or data[0].get("dataset_id")

ok = bool(payload) and payload.get("code") == 0 and bool(dataset_id)
print("__E2E_JSON__=" + json.dumps({{"ok": ok, "payload": payload, "dataset_id": dataset_id, "name": {name!r}}}, ensure_ascii=False))
""".strip(),
            timeout_s=60,
        )

    def _ragflow_delete_dataset(self, dataset_id: str) -> dict:
        return self._docker_exec_backend_py(
            f"""
from backend.services.ragflow_service import RagflowService
import json

svc = RagflowService()
dataset_id = {dataset_id!r}
payload = svc._http.delete_json(f"/api/v1/datasets/{dataset_id}") or {{}}
ok = bool(payload) and payload.get("code") == 0
print("__E2E_JSON__=" + json.dumps({{"ok": ok, "payload": payload, "dataset_id": {dataset_id!r}}}, ensure_ascii=False))
""".strip(),
            timeout_s=60,
        )

    def _ragflow_list_dataset_names(self) -> list[str]:
        res = self._docker_exec_backend_py(
            """
from backend.services.ragflow_service import RagflowService
import json

svc = RagflowService()
names = svc.list_all_kb_names()
print("__E2E_JSON__=" + json.dumps({"names": names}, ensure_ascii=False))
""".strip(),
            timeout_s=60,
        )
        names = res.get("names") or []
        return [str(x) for x in names if x]

    def _start_full_backup(self) -> BackupJobInfo:
        res = self._docker_exec_backend_py(
            """
from backend.app.modules.data_security.runner import start_job_if_idle
import json

job_id = start_job_if_idle(reason="e2e_destructive", full_backup=True)
print("__E2E_JSON__=" + json.dumps({"job_id": int(job_id)}, ensure_ascii=False))
""".strip(),
            timeout_s=60,
        )
        return BackupJobInfo(job_id=int(res["job_id"]), output_dir="", kind="full")

    def _wait_backup_done(self, job_id: int, *, timeout_s: int = 3600) -> BackupJobInfo:
        started = time.time()
        last = None
        while True:
            res = self._docker_exec_backend_py(
                f"""
from backend.services.data_security_store import DataSecurityStore
import json

store = DataSecurityStore()
j = store.get_job({job_id})
print("__E2E_JSON__=" + json.dumps(j.as_dict(), ensure_ascii=False))
""".strip(),
                timeout_s=60,
            )
            last = res
            status = res.get("status")
            if status in ("completed", "failed"):
                break
            if time.time() - started > timeout_s:
                raise AssertionError(f"backup job timeout: job={job_id} last={last}")
            time.sleep(5)

        if last.get("status") != "completed":
            raise AssertionError(f"backup failed: job={job_id} detail={last.get('detail')} message={last.get('message')}")
        out_dir = (last.get("output_dir") or "").strip()
        if not out_dir:
            raise AssertionError(f"backup job missing output_dir: {last}")
        return BackupJobInfo(job_id=job_id, output_dir=out_dir, kind=str(last.get("kind") or "full"))

    def _candidates_for_container_path(self, container_path: str) -> list[str]:
        s = (container_path or "").strip()
        if not s:
            return []
        # Match docker_utils fallback mappings + the historical split-backup layout.
        candidates = [s]
        if s.startswith("/app/data/backups"):
            candidates.append(s.replace("/app/data/backups", "/opt/ragflowauth/backups", 1))
            candidates.append(s.replace("/app/data/backups", "/opt/ragflowauth/data/backups", 1))
        if s.startswith("/app/data/") or s == "/app/data":
            candidates.append(s.replace("/app/data", "/opt/ragflowauth/data", 1))
        if s.startswith("/app/uploads/") or s == "/app/uploads":
            candidates.append(s.replace("/app/uploads", "/opt/ragflowauth/uploads", 1))
        # De-dup preserve order
        seen = set()
        out: list[str] = []
        for c in candidates:
            if c in seen:
                continue
            seen.add(c)
            out.append(c)
        return out

    def _resolve_backup_sources(self, container_pack_dir: str) -> tuple[str, str]:
        candidates = self._candidates_for_container_path(container_pack_dir)
        if not candidates:
            raise AssertionError(f"invalid pack_dir: {container_pack_dir!r}")

        auth_db_src = ""
        volumes_dir = ""

        for c in candidates:
            if not auth_db_src:
                ok = True
                try:
                    self._ssh(f"test -f {c}/auth.db", timeout_s=15)
                    auth_db_src = f"{c}/auth.db"
                except Exception:
                    ok = False
                _ = ok
            if not volumes_dir:
                try:
                    out = self._ssh(f"ls -1 {c}/volumes/*.tar.gz 2>/dev/null | head -1 || true", timeout_s=15).strip()
                    if out:
                        volumes_dir = f"{c}/volumes"
                except Exception:
                    pass
            if auth_db_src and volumes_dir:
                break

        if not auth_db_src:
            raise AssertionError(f"cannot find auth.db from candidates: {candidates}")
        if not volumes_dir:
            raise AssertionError(f"cannot find volumes/*.tar.gz from candidates: {candidates}")
        return auth_db_src, volumes_dir

    def _restore_from_pack_dir(self, container_pack_dir: str) -> None:
        auth_db_src, volumes_dir = self._resolve_backup_sources(container_pack_dir)

        # Restore auth DB
        self._ssh("docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true", timeout_s=60)

        # Copy auth.db
        self._ssh(f"cp -f {auth_db_src} /opt/ragflowauth/data/auth.db", timeout_s=60)

        # Stop ragflow containers (best-effort: anything named ragflow* except ragflowauth-*)
        ragflow_names = (
            self._ssh(
                "docker ps -a --format '{{.Names}}' | grep -i ragflow | grep -v '^ragflowauth-' || true",
                timeout_s=30,
            )
            .splitlines()
        )
        ragflow_names = [n.strip() for n in ragflow_names if n.strip()]
        if ragflow_names:
            self._ssh("docker stop " + " ".join(ragflow_names) + " 2>/dev/null || true", timeout_s=60)

        # Restore volumes
        self._ssh("docker image inspect alpine >/dev/null 2>&1 || docker pull alpine:latest", timeout_s=600)
        self._ssh(f"test -d {volumes_dir}", timeout_s=30)
        volume_files = self._ssh(f"ls -1 {volumes_dir}/*.tar.gz 2>/dev/null || true", timeout_s=30).splitlines()
        volume_files = [v.strip() for v in volume_files if v.strip()]
        if not volume_files:
            raise AssertionError(f"no volume backups found in {volumes_dir} (full backup should include ragflow volumes)")

        for vf in volume_files:
            volume_name = vf.split("/")[-1].removesuffix(".tar.gz")
            self._ssh(f"docker volume create {volume_name} >/dev/null 2>&1 || true", timeout_s=60)
            cmd = (
                "docker run --rm "
                f"-v {volume_name}:/data "
                f"-v {volumes_dir}:/backup:ro "
                f"alpine tar -xzf /backup/{volume_name}.tar.gz -C /data 2>&1"
            )
            self._ssh(cmd, timeout_s=900)

        # Start containers back
        self._ssh("docker start ragflowauth-backend ragflowauth-frontend 2>/dev/null || true", timeout_s=60)
        if ragflow_names:
            self._ssh("docker start " + " ".join(ragflow_names) + " 2>/dev/null || true", timeout_s=120)

        # Health check
        self._ssh("curl -fsS http://127.0.0.1:8001/health >/dev/null", timeout_s=60)

    def test_backup_restore_roundtrip_user_and_dataset(self) -> None:
        self._ensure_backup_target_local()

        # 1) Create canary user + dataset
        created_user = self._create_canary_user()
        self.assertTrue(self._user_exists(self.canary_username), "canary user not created")

        created_ds = self._ragflow_create_dataset(self.canary_dataset_name)
        self.assertTrue(created_ds.get("ok"), f"dataset create failed: {created_ds}")
        dataset_id = created_ds.get("dataset_id")
        self.assertTrue(dataset_id, f"missing dataset_id: {created_ds}")
        self.assertIn(self.canary_dataset_name, self._ragflow_list_dataset_names())

        # 2) Full backup
        started = self._start_full_backup()
        job = self._wait_backup_done(started.job_id, timeout_s=3600)

        # 3) Delete canaries
        self._delete_user_by_username(self.canary_username)
        self.assertFalse(self._user_exists(self.canary_username), "canary user not deleted")

        del_ds = self._ragflow_delete_dataset(str(dataset_id))
        self.assertTrue(del_ds.get("ok"), f"dataset delete failed: {del_ds}")
        self.assertNotIn(self.canary_dataset_name, self._ragflow_list_dataset_names())

        # 4) Restore from pack
        self._restore_from_pack_dir(job.output_dir)

        # 5) Verify restored
        self.assertTrue(self._user_exists(self.canary_username), "canary user not restored after restore")
        self.assertIn(self.canary_dataset_name, self._ragflow_list_dataset_names())

        # 6) Cleanup (best-effort): remove canaries to keep test env tidy
        try:
            self._delete_user_by_username(self.canary_username)
        except Exception:
            pass
