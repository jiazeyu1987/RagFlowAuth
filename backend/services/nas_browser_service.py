from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
from typing import Any

from backend.app.core.authz import AuthContext
from backend.app.core.config import settings


NAS_SERVER_IP = "172.30.30.4"
NAS_SHARE_NAME = "it共享"
NAS_USERNAME = "ceshi"
NAS_PASSWORD = "Kdlyx123"

_FOLDER_IMPORT_TASKS: dict[str, "NasFolderImportTask"] = {}
_TASK_LOCK = asyncio.Lock()


@dataclass(frozen=True)
class NasConfig:
    server: str = NAS_SERVER_IP
    share: str = NAS_SHARE_NAME
    username: str = NAS_USERNAME
    password: str = NAS_PASSWORD

    @property
    def root_unc(self) -> str:
        return f"\\\\{self.server}\\{self.share}"


@dataclass
class NasFolderImportTask:
    task_id: str
    folder_path: str
    kb_ref: str
    total_files: int
    processed_files: int = 0
    imported_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    status: str = "pending"
    current_file: str = ""
    error: str = ""
    imported: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["progress_percent"] = 100 if self.total_files == 0 else int((self.processed_files / self.total_files) * 100)
        payload["remaining_files"] = max(self.total_files - self.processed_files, 0)
        return payload


class NasBrowserService:
    def __init__(self, config: NasConfig | None = None) -> None:
        self.config = config or NasConfig()

    def _get_smbclient(self):
        try:
            import smbclient  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("NAS 功能依赖 smbprotocol，请先安装 backend/requirements.txt 中的依赖") from exc
        return smbclient

    def _normalize_relative_path(self, relative_path: str) -> str:
        raw = (relative_path or "").replace("\\", "/").strip()
        if not raw:
            return ""
        parts: list[str] = []
        for part in raw.split("/"):
            token = part.strip()
            if not token or token == ".":
                continue
            if token == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(token)
        return "/".join(parts)

    def _build_unc_path(self, relative_path: str) -> str:
        normalized = self._normalize_relative_path(relative_path)
        if not normalized:
            return self.config.root_unc
        normalized_windows = normalized.replace("/", "\\")
        return f"{self.config.root_unc}\\{normalized_windows}"

    def _relative_parent(self, relative_path: str) -> str | None:
        normalized = self._normalize_relative_path(relative_path)
        if not normalized:
            return None
        parent = str(PurePosixPath(normalized).parent)
        return "" if parent == "." else parent

    def _raise_browse_error(self, exc: Exception, normalized: str) -> None:
        message = str(exc or "").strip()
        lowered = message.lower()

        if isinstance(exc, FileNotFoundError):
            raise RuntimeError(f"NAS 路径不存在: {normalized or '/'}") from exc
        if "logon failure" in lowered or "authentication" in lowered or "access denied" in lowered:
            raise RuntimeError("NAS 认证失败，请检查用户名、密码和共享权限") from exc
        if "bad network name" in lowered or "network name cannot be found" in lowered:
            raise RuntimeError(f"NAS 共享不存在，请检查共享名称是否正确: {self.config.share}") from exc
        if "name not found" in lowered or "object path not found" in lowered or "cannot find the path" in lowered:
            raise RuntimeError(f"NAS 路径不存在: {normalized or '/'}") from exc
        if "connection" in lowered or "timeout" in lowered or "host is down" in lowered or "unreachable" in lowered:
            raise RuntimeError(f"NAS 连接失败，请检查服务器 {self.config.server} 是否可达") from exc
        raise RuntimeError(f"读取 NAS 目录失败: {message or exc.__class__.__name__}") from exc

    def _register_session(self, smbclient) -> None:
        smbclient.register_session(
            self.config.server,
            username=self.config.username,
            password=self.config.password,
        )

    def _allowed_extensions(self, deps) -> set[str]:
        allowed_extensions = set(settings.ALLOWED_EXTENSIONS)
        upload_settings_store = getattr(deps, "upload_settings_store", None)
        if upload_settings_store is not None:
            try:
                allowed_extensions = set(upload_settings_store.get().allowed_extensions)
            except Exception:
                allowed_extensions = set(settings.ALLOWED_EXTENSIONS)
        return {str(item).lower() for item in allowed_extensions}

    def _walk_files_sync(self, smbclient, relative_path: str) -> list[dict[str, str]]:
        normalized = self._normalize_relative_path(relative_path)
        unc_path = self._build_unc_path(normalized)
        files: list[dict[str, str]] = []
        for entry in smbclient.scandir(unc_path):
            item_relative_path = "/".join(part for part in [normalized, entry.name] if part)
            if entry.is_dir():
                files.extend(self._walk_files_sync(smbclient, item_relative_path))
                continue
            files.append({"name": entry.name, "path": item_relative_path})
        return files

    def _list_directory_sync(self, relative_path: str) -> dict[str, Any]:
        smbclient = self._get_smbclient()
        normalized = self._normalize_relative_path(relative_path)
        unc_path = self._build_unc_path(normalized)

        try:
            self._register_session(smbclient)
            items = []
            for entry in smbclient.scandir(unc_path):
                item_relative_path = "/".join(part for part in [normalized, entry.name] if part)
                stat = entry.stat()
                is_dir = entry.is_dir()
                items.append(
                    {
                        "name": entry.name,
                        "path": item_relative_path,
                        "is_dir": is_dir,
                        "size": 0 if is_dir else int(getattr(stat, "st_size", 0) or 0),
                        "modified_at": getattr(stat, "st_mtime", None),
                    }
                )
        except Exception as exc:
            self._raise_browse_error(exc, normalized)

        items.sort(key=lambda item: (not item["is_dir"], str(item["name"]).lower()))
        return {
            "current_path": normalized,
            "parent_path": self._relative_parent(normalized),
            "root_path": "",
            "items": items,
        }

    def _collect_folder_files_sync(self, relative_path: str, deps) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        smbclient = self._get_smbclient()
        normalized = self._normalize_relative_path(relative_path)
        try:
            self._register_session(smbclient)
            all_files = self._walk_files_sync(smbclient, normalized)
        except Exception as exc:
            self._raise_browse_error(exc, normalized)

        allowed_extensions = self._allowed_extensions(deps)
        supported_files: list[dict[str, str]] = []
        skipped_files: list[dict[str, Any]] = []
        for item in all_files:
            ext = PurePosixPath(item["path"]).suffix.lower()
            if ext not in allowed_extensions:
                skipped_files.append(
                    {
                        "path": item["path"],
                        "reason": "unsupported_extension",
                        "detail": f"unsupported extension: {ext or '<none>'}",
                    }
                )
                continue
            supported_files.append(item)
        return supported_files, skipped_files

    def _read_file_bytes_sync(self, source_path: str) -> bytes:
        smbclient = self._get_smbclient()
        normalized = self._normalize_relative_path(source_path)
        try:
            self._register_session(smbclient)
            unc_file_path = self._build_unc_path(normalized)
            with smbclient.open_file(unc_file_path, mode="rb") as fp:
                return fp.read()
        except Exception as exc:
            self._raise_browse_error(exc, normalized)

    async def list_directory(self, relative_path: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._list_directory_sync, relative_path)

    async def start_folder_import_task(self, *, relative_path: str, kb_ref: str, deps, ctx: AuthContext) -> dict[str, Any]:
        normalized = self._normalize_relative_path(relative_path)
        if not normalized:
            raise RuntimeError("请选择具体文件夹后再上传至知识库")

        supported_files, skipped_files = await asyncio.to_thread(self._collect_folder_files_sync, normalized, deps)
        task = NasFolderImportTask(
            task_id=uuid.uuid4().hex,
            folder_path=normalized,
            kb_ref=kb_ref,
            total_files=len(supported_files),
            skipped_count=len(skipped_files),
            skipped=skipped_files[:50],
            status="completed" if not supported_files else "pending",
        )

        async with _TASK_LOCK:
            _FOLDER_IMPORT_TASKS[task.task_id] = task

        if supported_files:
            ctx_copy = AuthContext(deps=ctx.deps, payload=ctx.payload, user=ctx.user, snapshot=ctx.snapshot)
            asyncio.create_task(
                self._run_folder_import_task(
                    task_id=task.task_id,
                    folder_path=normalized,
                    kb_ref=kb_ref,
                    files=supported_files,
                    deps=deps,
                    ctx=ctx_copy,
                )
            )

        return task.to_dict()

    async def get_folder_import_task(self, task_id: str) -> dict[str, Any]:
        async with _TASK_LOCK:
            task = _FOLDER_IMPORT_TASKS.get(task_id)
        if task is None:
            raise RuntimeError("NAS 上传任务不存在")
        return task.to_dict()

    async def import_file_to_kb(self, *, relative_path: str, kb_ref: str, deps, ctx) -> dict[str, Any]:
        normalized = self._normalize_relative_path(relative_path)
        if not normalized:
            raise RuntimeError("请选择具体文件后再上传至知识库")

        outcome = await self._import_single_file(
            source_path=normalized,
            target_filename=PurePosixPath(normalized).name,
            kb_ref=kb_ref,
            deps=deps,
            ctx=ctx,
        )
        imported = [outcome["payload"]] if outcome["status"] == "imported" else []
        skipped = [outcome["payload"]] if outcome["status"] == "skipped" else []
        failed = [outcome["payload"]] if outcome["status"] == "failed" else []
        return {
            "file_path": normalized,
            "kb_ref": kb_ref,
            "imported_count": len(imported),
            "skipped_count": len(skipped),
            "failed_count": len(failed),
            "imported": imported,
            "skipped": skipped,
            "failed": failed,
        }

    async def _run_folder_import_task(self, *, task_id: str, folder_path: str, kb_ref: str, files: list[dict[str, str]], deps, ctx: AuthContext) -> None:
        folder_name = PurePosixPath(folder_path).name or folder_path

        async with _TASK_LOCK:
            task = _FOLDER_IMPORT_TASKS.get(task_id)
            if task is None:
                return
            task.status = "running"

        try:
            for item in files:
                source_path = item["path"]
                target_filename = self._build_folder_target_filename(source_path, folder_path, folder_name)
                await self._update_task(task_id, current_file=source_path)
                outcome = await self._import_single_file(
                    source_path=source_path,
                    target_filename=target_filename,
                    kb_ref=kb_ref,
                    deps=deps,
                    ctx=ctx,
                )
                await self._apply_outcome(task_id, outcome)
                await asyncio.sleep(0)
            await self._complete_task(task_id)
        except Exception as exc:
            await self._fail_task(task_id, str(exc))

    async def _update_task(self, task_id: str, *, current_file: str) -> None:
        async with _TASK_LOCK:
            task = _FOLDER_IMPORT_TASKS.get(task_id)
            if task is not None:
                task.current_file = current_file

    async def _apply_outcome(self, task_id: str, outcome: dict[str, Any]) -> None:
        async with _TASK_LOCK:
            task = _FOLDER_IMPORT_TASKS.get(task_id)
            if task is None:
                return
            task.processed_files += 1
            task.current_file = ""
            if outcome["status"] == "imported":
                task.imported_count += 1
                if len(task.imported) < 50:
                    task.imported.append(outcome["payload"])
            elif outcome["status"] == "skipped":
                task.skipped_count += 1
                if len(task.skipped) < 50:
                    task.skipped.append(outcome["payload"])
            else:
                task.failed_count += 1
                if len(task.failed) < 50:
                    task.failed.append(outcome["payload"])

    async def _complete_task(self, task_id: str) -> None:
        async with _TASK_LOCK:
            task = _FOLDER_IMPORT_TASKS.get(task_id)
            if task is not None:
                task.status = "completed"
                task.current_file = ""

    async def _fail_task(self, task_id: str, error: str) -> None:
        async with _TASK_LOCK:
            task = _FOLDER_IMPORT_TASKS.get(task_id)
            if task is not None:
                task.status = "failed"
                task.error = error
                task.current_file = ""

    def _build_folder_target_filename(self, source_path: str, folder_path: str, folder_name: str) -> str:
        rel_inside_folder = str(PurePosixPath(source_path).relative_to(PurePosixPath(folder_path)))
        return f"{folder_name}/{rel_inside_folder}".replace("\\", "/")

    def _create_upload_file(self, filename: str, content: bytes):
        class _NasUploadFile:
            def __init__(self, file_name: str, file_content: bytes):
                self.filename = file_name
                self.content_type = None
                self._content = file_content

            async def read(self):
                return self._content

        return _NasUploadFile(filename, content)

    async def _import_single_file(self, *, source_path: str, target_filename: str, kb_ref: str, deps, ctx) -> dict[str, Any]:
        from backend.services.knowledge_ingestion.manager import KnowledgeIngestionManager

        ext = PurePosixPath(source_path).suffix.lower()
        if ext not in self._allowed_extensions(deps):
            return {
                "status": "skipped",
                "payload": {
                    "path": source_path,
                    "reason": "unsupported_extension",
                    "detail": f"unsupported extension: {ext or '<none>'}",
                },
            }

        try:
            content = await asyncio.to_thread(self._read_file_bytes_sync, source_path)
            ingestion_manager = getattr(deps, "knowledge_ingestion_manager", None) or KnowledgeIngestionManager(deps=deps)
            upload_file = self._create_upload_file(target_filename, content)
            doc = await ingestion_manager.stage_upload_knowledge(kb_ref=kb_ref, upload_file=upload_file, ctx=ctx)
        except Exception as exc:
            return {
                "status": "failed",
                "payload": {
                    "path": source_path,
                    "reason": "ingestion_failed",
                    "detail": str(exc),
                },
            }

        return {"status": "imported", "payload": {"doc_id": doc.doc_id, "filename": doc.filename}}
