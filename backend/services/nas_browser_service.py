from __future__ import annotations

import asyncio
import heapq
import itertools
import logging
import uuid
from pathlib import PurePosixPath
from types import SimpleNamespace
from typing import Any

from authx import TokenPayload

from backend.app.core.authz import AuthContext
from backend.app.core.config import settings
from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope, resolve_permissions
from backend.services.nas_task_store import NasTaskStore
from backend.services.unified_task_quota_service import UnifiedTaskQuotaService


logger = logging.getLogger(__name__)


NAS_SERVER_IP = "172.30.30.4"
NAS_SHARE_NAME = "it共享"
NAS_USERNAME = "ceshi"
NAS_PASSWORD = "Kdlyx123"

_TASK_LOCK = asyncio.Lock()


def _normalize_quota_limit(value: Any, fallback: int) -> int:
    try:
        normalized = int(value)
    except Exception:
        normalized = fallback
    return max(0, normalized)


_MAX_CONCURRENT_IMPORTS = _normalize_quota_limit(getattr(settings, "TASK_GLOBAL_CONCURRENCY_LIMIT", 2), 2)
_MAX_CONCURRENT_IMPORTS_PER_USER = _normalize_quota_limit(getattr(settings, "TASK_USER_CONCURRENCY_LIMIT", 1), 1)
_MAX_CONCURRENT_NAS_IMPORTS = _normalize_quota_limit(
    getattr(settings, "TASK_NAS_CONCURRENCY_LIMIT", _MAX_CONCURRENT_IMPORTS),
    _MAX_CONCURRENT_IMPORTS,
)
_RUNNING_TASKS: set[str] = set()
_RUNNING_TASK_META: dict[str, dict[str, str]] = {}
# Backward-compatible alias used by a few tests.
_ACTIVE_TASKS = _RUNNING_TASKS
_QUEUED_TASK_IDS: set[str] = set()
_QUEUED_TASK_HEAP: list[tuple[int, int, str, Any, AuthContext, str]] = []
_QUEUE_SEQUENCE = itertools.count()
_ACTIVE_STATUSES = {"pending", "running", "canceling", "pausing"}


class NasBrowserService:
    def __init__(
        self,
        *,
        task_store: NasTaskStore | None = None,
        server: str = NAS_SERVER_IP,
        share: str = NAS_SHARE_NAME,
        username: str = NAS_USERNAME,
        password: str = NAS_PASSWORD,
    ) -> None:
        self.server = server
        self.share = share
        self.username = username
        self.password = password
        self.root_unc = f"\\\\{self.server}\\{self.share}"
        self.task_store = task_store

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
            return self.root_unc
        normalized_windows = normalized.replace("/", "\\")
        return f"{self.root_unc}\\{normalized_windows}"

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
            raise RuntimeError(f"NAS 共享不存在，请检查共享名称是否正确: {self.share}") from exc
        if "name not found" in lowered or "object path not found" in lowered or "cannot find the path" in lowered:
            raise RuntimeError(f"NAS 路径不存在: {normalized or '/'}") from exc
        if "connection" in lowered or "timeout" in lowered or "host is down" in lowered or "unreachable" in lowered:
            raise RuntimeError(f"NAS 连接失败，请检查服务器 {self.server} 是否可达") from exc
        raise RuntimeError(f"读取 NAS 目录失败: {message or exc.__class__.__name__}") from exc

    def _register_session(self, smbclient) -> None:
        smbclient.register_session(
            self.server,
            username=self.username,
            password=self.password,
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

    def _store(self, deps):
        if self.task_store is not None:
            return self.task_store
        store = getattr(deps, "nas_task_store", None)
        if store is None:
            raise RuntimeError("nas_task_store 未初始化")
        return store

    @staticmethod
    def _clone_ctx(ctx: AuthContext) -> AuthContext:
        return AuthContext(deps=ctx.deps, payload=ctx.payload, user=ctx.user, snapshot=ctx.snapshot)

    @staticmethod
    def _normalize_path_list(items: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for item in items:
            path = str(item or "").replace("\\", "/").strip()
            if not path or path in seen:
                continue
            seen.add(path)
            normalized.append(path)
        return normalized

    @staticmethod
    def _extract_retry_paths(task) -> list[str]:
        paths: list[str] = []
        for item in task.failed or []:
            if isinstance(item, dict):
                value = str(item.get("path") or "").strip()
            else:
                value = str(item or "").strip()
            if value:
                paths.append(value)
        return NasBrowserService._normalize_path_list(paths)

    @staticmethod
    def _normalize_priority(value: Any) -> int:
        try:
            normalized = int(value)
        except Exception:
            normalized = 100
        # Lower number means higher priority.
        return max(1, min(normalized, 1000))

    @staticmethod
    def _task_owner_id_from_task(task: Any) -> str:
        owner = str(getattr(task, "created_by_user_id", "") or "").strip()
        return owner or "__system__"

    @staticmethod
    def _task_owner_id_from_dict(task_dict: dict[str, Any]) -> str:
        owner = str(task_dict.get("created_by_user_id") or "").strip()
        return owner or "__system__"

    @staticmethod
    def _quota_limits() -> dict[str, int]:
        return {
            "global": _normalize_quota_limit(_MAX_CONCURRENT_IMPORTS, 2),
            "per_user": _normalize_quota_limit(_MAX_CONCURRENT_IMPORTS_PER_USER, 1),
            "task_kind": _normalize_quota_limit(_MAX_CONCURRENT_NAS_IMPORTS, 2),
        }

    @staticmethod
    def _task_payload_base(task_dict: dict[str, Any]) -> dict[str, Any]:
        total_files = int(task_dict.get("total_files") or 0)
        processed_files = int(task_dict.get("processed_files") or 0)
        pending_files = task_dict.pop("pending_files", []) or []
        status = str(task_dict.get("status") or "pending")
        task_dict["progress_percent"] = 100 if total_files == 0 else int((processed_files / total_files) * 100)
        task_dict["remaining_files"] = max(total_files - processed_files, 0)
        task_dict["pending_files_count"] = len(pending_files)
        task_dict["task_priority"] = NasBrowserService._normalize_priority(task_dict.get("priority"))
        task_dict["can_cancel"] = status in ("pending", "running", "canceling", "paused", "pausing")
        task_dict["can_pause"] = status in ("pending", "running", "pausing")
        task_dict["can_resume"] = status in ("paused", "pausing")
        task_dict["can_retry"] = status in ("failed", "canceled") or (
            status == "completed" and int(task_dict.get("failed_count") or 0) > 0
        )
        task_dict["owner_user_id"] = NasBrowserService._task_owner_id_from_dict(task_dict)
        return task_dict

    async def _queue_snapshot(self) -> list[str]:
        async with _TASK_LOCK:
            pending = sorted(
                (priority, sequence, task_id)
                for priority, sequence, task_id, _deps, _ctx, _owner_user_id in _QUEUED_TASK_HEAP
                if task_id in _QUEUED_TASK_IDS
            )
        queue: list[str] = []
        seen: set[str] = set()
        for _priority, _sequence, task_id in pending:
            if task_id in seen:
                continue
            seen.add(task_id)
            queue.append(task_id)
        return queue

    async def _queue_position(self, task_id: str) -> int | None:
        if not task_id:
            return None
        queue = await self._queue_snapshot()
        try:
            return queue.index(task_id) + 1
        except ValueError:
            return None

    async def _is_task_running(self, task_id: str) -> bool:
        async with _TASK_LOCK:
            return task_id in _RUNNING_TASKS

    async def _drop_task_from_queue(self, task_id: str) -> None:
        async with _TASK_LOCK:
            _QUEUED_TASK_IDS.discard(task_id)

    @staticmethod
    def _running_owner_count_locked(owner_user_id: str) -> int:
        return sum(1 for meta in _RUNNING_TASK_META.values() if meta.get("owner_user_id") == owner_user_id)

    @staticmethod
    def _running_kind_count_locked(task_kind: str) -> int:
        return sum(1 for meta in _RUNNING_TASK_META.values() if meta.get("task_kind") == task_kind)

    async def _quota_block_reason(self, owner_user_id: str) -> str | None:
        limits = self._quota_limits()
        async with _TASK_LOCK:
            running_total = len(_RUNNING_TASKS)
            running_owner = self._running_owner_count_locked(owner_user_id)
            running_kind = self._running_kind_count_locked("nas_import")

        if limits["global"] <= 0 or running_total >= limits["global"]:
            return "global_limit"
        if limits["task_kind"] <= 0 or running_kind >= limits["task_kind"]:
            return "task_kind_limit"
        if limits["per_user"] <= 0 or running_owner >= limits["per_user"]:
            return "user_limit"
        return None

    async def _task_payload(self, task_dict: dict[str, Any]) -> dict[str, Any]:
        payload = self._task_payload_base(task_dict)
        status = str(payload.get("status") or "")
        task_id = str(payload.get("task_id") or "")
        owner_user_id = self._task_owner_id_from_dict(payload)
        limits = self._quota_limits()
        queue_position = await self._queue_position(task_id) if status == "pending" else None
        payload["queue_position"] = queue_position
        payload["is_queued"] = queue_position is not None
        payload["max_concurrency"] = limits["global"]
        payload["task_kind"] = "nas_import"
        payload["quota"] = {
            "global_limit": limits["global"],
            "task_kind_limit": limits["task_kind"],
            "per_user_limit": limits["per_user"],
        }
        payload["quota_blocked_reason"] = (
            await self._quota_block_reason(owner_user_id) if status == "pending" and queue_position else None
        )
        return payload

    @staticmethod
    def _system_recovery_snapshot() -> PermissionSnapshot:
        return PermissionSnapshot(
            is_admin=True,
            can_upload=True,
            can_review=True,
            can_download=True,
            can_delete=True,
            kb_scope=ResourceScope.ALL,
            kb_names=frozenset(),
            chat_scope=ResourceScope.ALL,
            chat_ids=frozenset(),
        )

    def _build_recovery_ctx(self, *, deps, owner_user_id: str) -> AuthContext:
        actor = str(owner_user_id or "").strip() or "system_recovery"
        user_store = getattr(deps, "user_store", None)
        user = user_store.get_by_user_id(actor) if user_store is not None else None
        if user is not None:
            snapshot = resolve_permissions(deps, user)
            return AuthContext(
                deps=deps,
                payload=TokenPayload(sub=actor),
                user=user,
                snapshot=snapshot,
            )
        return AuthContext(
            deps=deps,
            payload=TokenPayload(sub=actor),
            user=SimpleNamespace(user_id=actor, role="admin"),
            snapshot=self._system_recovery_snapshot(),
        )

    async def recover_startup_tasks(self, *, deps, limit: int = 500) -> dict[str, int]:
        store = self._store(deps)
        async with _TASK_LOCK:
            _RUNNING_TASKS.clear()
            _RUNNING_TASK_META.clear()
            _QUEUED_TASK_IDS.clear()
            _QUEUED_TASK_HEAP.clear()

        active_tasks = await asyncio.to_thread(
            store.list_tasks_by_statuses,
            list(_ACTIVE_STATUSES),
            limit=limit,
        )
        summary = {
            "scanned": len(active_tasks),
            "requeued": 0,
            "canceled": 0,
            "paused": 0,
            "completed": 0,
        }

        for task in active_tasks:
            pending_files = self._normalize_path_list(list(task.pending_files or []))
            if pending_files != list(task.pending_files or []):
                task = await asyncio.to_thread(store.update_task, task.task_id, pending_files=pending_files) or task

            if task.cancel_requested_at_ms is not None or task.status == "canceling":
                await asyncio.to_thread(
                    store.update_task,
                    task.task_id,
                    status="canceled",
                    current_file="",
                    error="",
                )
                await self._drop_task_from_queue(task.task_id)
                summary["canceled"] += 1
                continue

            if task.status == "pausing":
                await asyncio.to_thread(store.update_task, task.task_id, status="paused", current_file="")
                await self._drop_task_from_queue(task.task_id)
                summary["paused"] += 1
                continue

            if task.status == "running":
                task = await asyncio.to_thread(
                    store.update_task,
                    task.task_id,
                    status="pending",
                    current_file="",
                    error="",
                ) or task

            if not pending_files:
                if task.status in ("pending", "running"):
                    await asyncio.to_thread(store.update_task, task.task_id, status="completed", current_file="", error="")
                    summary["completed"] += 1
                continue

            recovery_ctx = self._build_recovery_ctx(
                deps=deps,
                owner_user_id=self._task_owner_id_from_task(task),
            )
            self._schedule_folder_import_task(
                task_id=task.task_id,
                deps=deps,
                ctx=recovery_ctx,
            )
            summary["requeued"] += 1

        if summary["scanned"] > 0:
            logger.info("nas_task_recovery summary=%s", summary)
        return summary

    async def list_directory(self, relative_path: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._list_directory_sync, relative_path)

    async def start_folder_import_task(
        self,
        *,
        relative_path: str,
        kb_ref: str,
        deps,
        ctx: AuthContext,
        priority: int | None = None,
    ) -> dict[str, Any]:
        normalized = self._normalize_relative_path(relative_path)
        if not normalized:
            raise RuntimeError("请选择具体文件夹后再上传至知识库")

        supported_files, skipped_files = await asyncio.to_thread(self._collect_folder_files_sync, normalized, deps)
        task_id = uuid.uuid4().hex
        store = self._store(deps)
        task_priority = self._normalize_priority(priority)
        pending_files = self._normalize_path_list([item.get("path") or "" for item in supported_files])
        actor_user_id = str(getattr(getattr(ctx, "payload", None), "sub", "") or "")

        if pending_files:
            UnifiedTaskQuotaService().assert_can_start(
                deps=deps,
                actor_user_id=actor_user_id,
                task_kind=UnifiedTaskQuotaService.NAS_KIND,
            )

        task = await asyncio.to_thread(
            store.create_task,
            task_id=task_id,
            folder_path=normalized,
            kb_ref=kb_ref,
            created_by_user_id=actor_user_id,
            total_files=len(pending_files),
            skipped_count=len(skipped_files),
            skipped=skipped_files[:50],
            pending_files=pending_files,
            priority=task_priority,
            status="completed" if not pending_files else "pending",
        )

        if pending_files:
            self._schedule_folder_import_task(task_id=task_id, deps=deps, ctx=self._clone_ctx(ctx))

        return await self._task_payload(task.as_dict())

    async def get_folder_import_task(self, task_id: str, deps=None, ctx: AuthContext | None = None) -> dict[str, Any]:
        if deps is None and self.task_store is None:
            raise RuntimeError("缺少依赖上下文")
        store = self._store(deps)
        task = await asyncio.to_thread(store.get_task, task_id)
        if task is None:
            raise RuntimeError("NAS 上传任务不存在")
        if ctx is not None and task.status in ("pending", "running") and task.pending_files:
            self._schedule_folder_import_task(task_id=task_id, deps=deps, ctx=self._clone_ctx(ctx))
        return await self._task_payload(task.as_dict())

    async def cancel_folder_import_task(self, task_id: str, *, deps) -> dict[str, Any]:
        store = self._store(deps)
        task = await asyncio.to_thread(store.request_cancel_task, task_id)
        if task is None:
            raise RuntimeError("NAS 上传任务不存在")
        if task.status == "canceling":
            async with _TASK_LOCK:
                running = task_id in _RUNNING_TASKS
            if not running:
                task = await asyncio.to_thread(
                    store.update_task,
                    task_id,
                    status="canceled",
                    current_file="",
                    error="",
                )
        if task.status == "canceled":
            await self._drop_task_from_queue(task_id)
        return await self._task_payload(task.as_dict())

    async def pause_folder_import_task(self, task_id: str, *, deps) -> dict[str, Any]:
        store = self._store(deps)
        task = await asyncio.to_thread(store.request_pause_task, task_id)
        if task is None:
            raise RuntimeError("NAS 上传任务不存在")
        if task.status == "pausing":
            async with _TASK_LOCK:
                running = task_id in _RUNNING_TASKS
            if not running:
                task = await asyncio.to_thread(store.update_task, task_id, status="paused", current_file="")
        if task.status == "paused":
            await self._drop_task_from_queue(task_id)
        return await self._task_payload(task.as_dict())

    async def resume_folder_import_task(self, task_id: str, *, deps, ctx: AuthContext) -> dict[str, Any]:
        store = self._store(deps)
        task = await asyncio.to_thread(store.request_resume_task, task_id)
        if task is None:
            raise RuntimeError("NAS 上传任务不存在")
        if task.status == "pending" and task.pending_files:
            self._schedule_folder_import_task(task_id=task_id, deps=deps, ctx=self._clone_ctx(ctx))
        return await self._task_payload(task.as_dict())

    async def retry_folder_import_task(self, task_id: str, *, deps, ctx: AuthContext) -> dict[str, Any]:
        store = self._store(deps)
        async with _TASK_LOCK:
            task = await asyncio.to_thread(store.get_task, task_id)
            if task is None:
                raise RuntimeError("NAS 上传任务不存在")
            if task_id in _ACTIVE_TASKS or task.status in _ACTIVE_STATUSES:
                raise RuntimeError("任务仍在执行，暂不支持重试")

            retry_paths = self._normalize_path_list(list(task.pending_files or []))
            if not retry_paths:
                retry_paths = self._extract_retry_paths(task)
            if not retry_paths:
                raise RuntimeError("任务没有可重试的文件")

            reset_task = await asyncio.to_thread(
                store.update_task,
                task_id,
                status="pending",
                total_files=len(retry_paths),
                processed_files=0,
                imported_count=0,
                skipped_count=0,
                failed_count=0,
                current_file="",
                error="",
                imported=[],
                skipped=[],
                failed=[],
                pending_files=retry_paths,
                retry_count=int(task.retry_count or 0) + 1,
                cancel_requested_at_ms=None,
            )

        self._schedule_folder_import_task(task_id=task_id, deps=deps, ctx=self._clone_ctx(ctx))
        return await self._task_payload(reset_task.as_dict())

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

    def _schedule_folder_import_task(self, *, task_id: str, deps, ctx: AuthContext) -> None:
        async def _enqueue() -> None:
            store = self._store(deps)
            task = await asyncio.to_thread(store.get_task, task_id)
            if task is None or not task.pending_files:
                return
            priority = self._normalize_priority(task.priority)
            owner_user_id = self._task_owner_id_from_task(task)
            async with _TASK_LOCK:
                if task_id in _RUNNING_TASKS:
                    return
                _QUEUED_TASK_IDS.add(task_id)
                heapq.heappush(
                    _QUEUED_TASK_HEAP,
                    (priority, next(_QUEUE_SEQUENCE), task_id, deps, self._clone_ctx(ctx), owner_user_id),
                )
            await self._drain_task_queue()

        asyncio.create_task(_enqueue())

    async def _drain_task_queue(self) -> None:
        limits = self._quota_limits()
        while True:
            deferred_items: list[tuple[int, int, str, Any, AuthContext, str]] = []
            async with _TASK_LOCK:
                running_total = len(_RUNNING_TASKS)
                running_kind = self._running_kind_count_locked("nas_import")
                if limits["global"] <= 0 or running_total >= limits["global"]:
                    return
                if limits["task_kind"] <= 0 or running_kind >= limits["task_kind"]:
                    return

                next_item: tuple[str, Any, AuthContext] | None = None
                while _QUEUED_TASK_HEAP:
                    priority, sequence, task_id, deps, ctx, owner_user_id = heapq.heappop(_QUEUED_TASK_HEAP)
                    if task_id not in _QUEUED_TASK_IDS:
                        continue
                    if task_id in _RUNNING_TASKS:
                        _QUEUED_TASK_IDS.discard(task_id)
                        continue
                    if limits["per_user"] <= 0 or self._running_owner_count_locked(owner_user_id) >= limits["per_user"]:
                        deferred_items.append((priority, sequence, task_id, deps, ctx, owner_user_id))
                        continue
                    _QUEUED_TASK_IDS.discard(task_id)
                    _RUNNING_TASKS.add(task_id)
                    _RUNNING_TASK_META[task_id] = {
                        "owner_user_id": owner_user_id,
                        "task_kind": "nas_import",
                    }
                    next_item = (task_id, deps, ctx)
                    break

                for item in deferred_items:
                    heapq.heappush(_QUEUED_TASK_HEAP, item)

            if next_item is None:
                return
            asyncio.create_task(self._run_queued_task(task_id=next_item[0], deps=next_item[1], ctx=next_item[2]))

    async def _run_queued_task(self, *, task_id: str, deps, ctx: AuthContext) -> None:
        try:
            await self._run_folder_import_task(task_id=task_id, deps=deps, ctx=ctx)
        finally:
            async with _TASK_LOCK:
                _RUNNING_TASKS.discard(task_id)
                _RUNNING_TASK_META.pop(task_id, None)
            await self._drain_task_queue()

    async def _is_cancel_requested(self, task_id: str, deps) -> bool:
        store = self._store(deps)
        task = await asyncio.to_thread(store.get_task, task_id)
        if task is None:
            return True
        if task.status == "canceled":
            return True
        return task.cancel_requested_at_ms is not None or task.status == "canceling"

    async def _is_pause_requested(self, task_id: str, deps) -> bool:
        store = self._store(deps)
        task = await asyncio.to_thread(store.get_task, task_id)
        if task is None:
            return False
        return task.status in ("paused", "pausing")

    async def _take_next_pending_file(self, task_id: str, deps) -> str | None:
        store = self._store(deps)
        async with _TASK_LOCK:
            task = await asyncio.to_thread(store.get_task, task_id)
            if task is None:
                return None
            pending_files = list(task.pending_files or [])
            while pending_files:
                next_path = str(pending_files.pop(0) or "").strip()
                if not next_path:
                    continue
                await asyncio.to_thread(store.update_task, task_id, pending_files=pending_files)
                return next_path
            await asyncio.to_thread(store.update_task, task_id, pending_files=[])
            return None

    async def _run_folder_import_task(self, *, task_id: str, deps, ctx: AuthContext) -> None:
        store = self._store(deps)
        task = await asyncio.to_thread(store.get_task, task_id)
        if task is None:
            return

        if await self._is_cancel_requested(task_id, deps):
            await asyncio.to_thread(store.update_task, task_id, status="canceled", current_file="", error="")
            return

        if task.status in ("paused", "pausing"):
            await asyncio.to_thread(store.update_task, task_id, status="paused", current_file="")
            return

        if not task.pending_files:
            await asyncio.to_thread(store.update_task, task_id, status="completed", current_file="", error="")
            return

        folder_path = task.folder_path
        kb_ref = task.kb_ref
        folder_name = PurePosixPath(folder_path).name or folder_path
        await asyncio.to_thread(store.update_task, task_id, status="running", current_file="", error="")

        try:
            while True:
                if await self._is_cancel_requested(task_id, deps):
                    await asyncio.to_thread(store.update_task, task_id, status="canceled", current_file="", error="")
                    return

                if await self._is_pause_requested(task_id, deps):
                    await asyncio.to_thread(store.update_task, task_id, status="paused", current_file="", error="")
                    return

                source_path = await self._take_next_pending_file(task_id, deps)
                if not source_path:
                    break

                target_filename = self._build_folder_target_filename(source_path, folder_path, folder_name)
                await asyncio.to_thread(store.update_task, task_id, current_file=source_path)
                outcome = await self._import_single_file(
                    source_path=source_path,
                    target_filename=target_filename,
                    kb_ref=kb_ref,
                    deps=deps,
                    ctx=ctx,
                )
                await self._apply_outcome(task_id, outcome, source_path, deps)
                await asyncio.sleep(0)

            final_task = await asyncio.to_thread(store.get_task, task_id)
            if final_task is None:
                return
            if final_task.cancel_requested_at_ms is not None or final_task.status == "canceling":
                await asyncio.to_thread(store.update_task, task_id, status="canceled", current_file="", error="")
                return
            await asyncio.to_thread(store.update_task, task_id, status="completed", current_file="", error="")
        except Exception as exc:
            await asyncio.to_thread(store.update_task, task_id, status="failed", error=str(exc), current_file="")

    async def _apply_outcome(self, task_id: str, outcome: dict[str, Any], source_path: str, deps) -> None:
        store = self._store(deps)
        async with _TASK_LOCK:
            task = await asyncio.to_thread(store.get_task, task_id)
            if task is None:
                return

            imported = list(task.imported or [])
            skipped = list(task.skipped or [])
            failed = list(task.failed or [])

            processed_files = int(task.processed_files or 0) + 1
            imported_count = int(task.imported_count or 0)
            skipped_count = int(task.skipped_count or 0)
            failed_count = int(task.failed_count or 0)

            if outcome["status"] == "imported":
                imported_count += 1
                if len(imported) < 50:
                    imported.append(outcome["payload"])
            elif outcome["status"] == "skipped":
                skipped_count += 1
                if len(skipped) < 50:
                    skipped.append(outcome["payload"])
            else:
                payload = dict(outcome.get("payload") or {})
                payload.setdefault("path", source_path)
                failed_count += 1
                if len(failed) < 50:
                    failed.append(payload)

            await asyncio.to_thread(
                store.update_task,
                task_id,
                processed_files=processed_files,
                imported_count=imported_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                imported=imported,
                skipped=skipped,
                failed=failed,
                current_file="",
            )

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
