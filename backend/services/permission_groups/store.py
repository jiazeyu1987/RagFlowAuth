"""
增强型权限组数据存储服务
支持资源配置（知识库、聊天体）和细粒度操作权限
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from backend.database.sqlite import connect_sqlite

_UNSET = object()


class PermissionGroupStore:
    def __init__(self, database_path: str, logger: logging.Logger = None):
        self._database_path = database_path
        self._logger = logger or logging.getLogger(__name__)

    def _count_users_in_group(self, cursor: sqlite3.Cursor, group_id: int) -> int:
        try:
            cursor.execute(
                "SELECT COUNT(*) as count FROM user_permission_groups WHERE group_id = ?",
                (group_id,),
            )
            row = cursor.fetchone()
            return int((row["count"] if row else 0) or 0)
        except sqlite3.OperationalError:
            # Older DB missing user_permission_groups: treat as 0 (we no longer read users.group_id).
            return 0

    def _get_connection(self) -> sqlite3.Connection:
        return connect_sqlite(self._database_path)

    def create_group(
        self,
        group_name: str,
        description: str = None,
        created_by: str | None = None,
        folder_id: str | None = None,
        accessible_kbs: List[str] = None,
        accessible_kb_nodes: List[str] = None,
        accessible_chats: List[str] = None,
        accessible_tools: List[str] = None,
        can_upload: bool = False,
        can_review: bool = False,
        can_download: bool = True,
        can_copy: bool = False,
        can_delete: bool = False,
        can_manage_kb_directory: bool = False,
        can_view_kb_config: bool = True,
        can_view_tools: bool = True,
    ) -> Optional[int]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT group_id FROM permission_groups WHERE group_name = ?", (group_name,))
                if cursor.fetchone():
                    self._logger.warning(f"权限组已存在: {group_name}")
                    return None

                cursor.execute(
                    """
                    INSERT INTO permission_groups (
                        group_name, description, created_by, folder_id, is_system,
                        accessible_kbs, accessible_kb_nodes, accessible_chats, accessible_tools,
                        can_upload, can_review, can_download, can_copy, can_delete, can_manage_kb_directory,
                        can_view_kb_config, can_view_tools
                    ) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        group_name,
                        description,
                        (str(created_by).strip() if isinstance(created_by, str) and created_by.strip() else None),
                        (str(folder_id).strip() if isinstance(folder_id, str) and folder_id.strip() else None),
                        json.dumps(accessible_kbs or []),
                        json.dumps(accessible_kb_nodes or []),
                        json.dumps(accessible_chats or []),
                        json.dumps(accessible_tools or []),
                        1 if can_upload else 0,
                        1 if can_review else 0,
                        1 if can_download else 0,
                        1 if can_copy else 0,
                        1 if can_delete else 0,
                        1 if can_manage_kb_directory else 0,
                        1 if can_view_kb_config else 0,
                        1 if can_view_tools else 0,
                    ),
                )
                group_id = cursor.lastrowid

                conn.commit()
                self._logger.info(f"创建权限组成功: {group_name} (ID: {group_id})")
                return group_id

        except Exception as e:
            self._logger.error(f"创建权限组失败: {e}")
            return None

    def get_group(self, group_id: int) -> Optional[Dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT group_id, group_name, description, is_system, created_by,
                           folder_id,
                           accessible_kbs, accessible_kb_nodes, accessible_chats, accessible_tools,
                           can_upload, can_review, can_download, can_copy, can_delete, can_manage_kb_directory,
                           can_view_kb_config, can_view_tools,
                           created_at, updated_at
                    FROM permission_groups
                    WHERE group_id = ?
                    """,
                    (group_id,),
                )
                row = cursor.fetchone()

                if not row:
                    return None

                group = dict(row)
                group["accessible_kbs"] = json.loads(group["accessible_kbs"] or "[]")
                group["accessible_kb_nodes"] = json.loads(group.get("accessible_kb_nodes") or "[]")
                group["accessible_chats"] = json.loads(group["accessible_chats"] or "[]")
                group["accessible_tools"] = json.loads(group.get("accessible_tools") or "[]")

                group["can_upload"] = bool(group["can_upload"])
                group["can_review"] = bool(group["can_review"])
                group["can_download"] = bool(group["can_download"])
                group["can_copy"] = bool(group.get("can_copy"))
                group["can_delete"] = bool(group["can_delete"])
                group["can_manage_kb_directory"] = bool(group.get("can_manage_kb_directory"))
                group["can_view_kb_config"] = bool(group.get("can_view_kb_config"))
                group["can_view_tools"] = bool(group.get("can_view_tools"))

                group["user_count"] = self._count_users_in_group(cursor, group_id)
                return group

        except Exception as e:
            self._logger.error(f"获取权限组失败: {e}")
            return None

    def get_group_by_name(self, group_name: str) -> Optional[Dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT group_id, group_name, description, is_system, created_by,
                           folder_id,
                           accessible_kbs, accessible_kb_nodes, accessible_chats, accessible_tools,
                           can_upload, can_review, can_download, can_copy, can_delete, can_manage_kb_directory,
                           can_view_kb_config, can_view_tools,
                           created_at, updated_at
                    FROM permission_groups
                    WHERE group_name = ?
                    """,
                    (group_name,),
                )
                row = cursor.fetchone()

                if not row:
                    return None

                group = dict(row)
                group["accessible_kbs"] = json.loads(group["accessible_kbs"] or "[]")
                group["accessible_kb_nodes"] = json.loads(group.get("accessible_kb_nodes") or "[]")
                group["accessible_chats"] = json.loads(group["accessible_chats"] or "[]")
                group["accessible_tools"] = json.loads(group.get("accessible_tools") or "[]")
                group["can_upload"] = bool(group["can_upload"])
                group["can_review"] = bool(group["can_review"])
                group["can_download"] = bool(group["can_download"])
                group["can_copy"] = bool(group.get("can_copy"))
                group["can_delete"] = bool(group["can_delete"])
                group["can_manage_kb_directory"] = bool(group.get("can_manage_kb_directory"))
                group["can_view_kb_config"] = bool(group.get("can_view_kb_config"))
                group["can_view_tools"] = bool(group.get("can_view_tools"))

                group["user_count"] = self._count_users_in_group(cursor, int(group["group_id"]))
                return group

        except Exception as e:
            self._logger.error(f"获取权限组失败: {e}")
            return None

    def list_groups(self) -> List[Dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT group_id, group_name, description, is_system, created_by,
                           folder_id,
                           accessible_kbs, accessible_kb_nodes, accessible_chats, accessible_tools,
                           can_upload, can_review, can_download, can_copy, can_delete, can_manage_kb_directory,
                           can_view_kb_config, can_view_tools,
                           created_at, updated_at
                    FROM permission_groups
                    ORDER BY group_id
                    """
                )
                groups = []

                for row in cursor.fetchall():
                    group = dict(row)
                    group["accessible_kbs"] = json.loads(group["accessible_kbs"] or "[]")
                    group["accessible_kb_nodes"] = json.loads(group.get("accessible_kb_nodes") or "[]")
                    group["accessible_chats"] = json.loads(group["accessible_chats"] or "[]")
                    group["accessible_tools"] = json.loads(group.get("accessible_tools") or "[]")
                    group["can_upload"] = bool(group["can_upload"])
                    group["can_review"] = bool(group["can_review"])
                    group["can_download"] = bool(group["can_download"])
                    group["can_copy"] = bool(group.get("can_copy"))
                    group["can_delete"] = bool(group["can_delete"])
                    group["can_manage_kb_directory"] = bool(group.get("can_manage_kb_directory"))
                    group["can_view_kb_config"] = bool(group.get("can_view_kb_config"))
                    group["can_view_tools"] = bool(group.get("can_view_tools"))

                    group["user_count"] = self._count_users_in_group(cursor, int(group["group_id"]))
                    groups.append(group)

                return groups

        except Exception as e:
            self._logger.error(f"列出权限组失败: {e}")
            return []

    def update_group(
        self,
        group_id: int,
        group_name: str = None,
        description: str = None,
        folder_id: str | None | object = _UNSET,
        accessible_kbs: List[str] = None,
        accessible_kb_nodes: List[str] = None,
        accessible_chats: List[str] = None,
        accessible_tools: List[str] = None,
        can_upload: bool = None,
        can_review: bool = None,
        can_download: bool = None,
        can_copy: bool = None,
        can_delete: bool = None,
        can_manage_kb_directory: bool = None,
        can_view_kb_config: bool = None,
        can_view_tools: bool = None,
    ) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT group_id FROM permission_groups WHERE group_id = ?", (group_id,))
                if not cursor.fetchone():
                    return False

                updates = []
                params = []

                if group_name is not None:
                    updates.append("group_name = ?")
                    params.append(group_name)
                if description is not None:
                    updates.append("description = ?")
                    params.append(description)
                if folder_id is not _UNSET:
                    clean_folder_id = str(folder_id).strip() if isinstance(folder_id, str) and folder_id.strip() else None
                    updates.append("folder_id = ?")
                    params.append(clean_folder_id)
                if accessible_kbs is not None:
                    updates.append("accessible_kbs = ?")
                    params.append(json.dumps(accessible_kbs))
                if accessible_kb_nodes is not None:
                    updates.append("accessible_kb_nodes = ?")
                    params.append(json.dumps(accessible_kb_nodes))
                if accessible_chats is not None:
                    updates.append("accessible_chats = ?")
                    params.append(json.dumps(accessible_chats))
                if accessible_tools is not None:
                    updates.append("accessible_tools = ?")
                    params.append(json.dumps(accessible_tools))
                if can_upload is not None:
                    updates.append("can_upload = ?")
                    params.append(1 if can_upload else 0)
                if can_review is not None:
                    updates.append("can_review = ?")
                    params.append(1 if can_review else 0)
                if can_download is not None:
                    updates.append("can_download = ?")
                    params.append(1 if can_download else 0)
                if can_copy is not None:
                    updates.append("can_copy = ?")
                    params.append(1 if can_copy else 0)
                if can_delete is not None:
                    updates.append("can_delete = ?")
                    params.append(1 if can_delete else 0)
                if can_manage_kb_directory is not None:
                    updates.append("can_manage_kb_directory = ?")
                    params.append(1 if can_manage_kb_directory else 0)
                if can_view_kb_config is not None:
                    updates.append("can_view_kb_config = ?")
                    params.append(1 if can_view_kb_config else 0)
                if can_view_tools is not None:
                    updates.append("can_view_tools = ?")
                    params.append(1 if can_view_tools else 0)

                updates.append("updated_at = ?")
                params.append(datetime.now())

                if not updates:
                    return True

                params.append(group_id)
                cursor.execute(
                    f"UPDATE permission_groups SET {', '.join(updates)} WHERE group_id = ?",
                    params,
                )
                conn.commit()
                return True
        except Exception as e:
            self._logger.error(f"更新权限组失败: {e}")
            return False

    def delete_group(self, group_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT is_system FROM permission_groups WHERE group_id = ?", (group_id,))
                row = cursor.fetchone()
                if not row:
                    return False
                if bool(row["is_system"]):
                    self._logger.warning(f"系统权限组不可删除: {group_id}")
                    return False

                user_count = self._count_users_in_group(cursor, group_id)
                if user_count > 0:
                    self._logger.warning(f"权限组存在用户，无法删除: {group_id} user_count={user_count}")
                    return False

                cursor.execute("DELETE FROM permission_groups WHERE group_id = ?", (group_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self._logger.error(f"删除权限组失败: {e}")
            return False
