import time
from dataclasses import dataclass
from typing import Optional

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


@dataclass(frozen=True)
class Company:
    company_id: int
    name: str
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True)
class Department:
    department_id: int
    name: str
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True)
class OrgDirectoryAuditLog:
    id: int
    entity_type: str
    action: str
    entity_id: Optional[int]
    before_name: Optional[str]
    after_name: Optional[str]
    actor_user_id: str
    created_at_ms: int


class OrgDirectoryStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        return connect_sqlite(self.db_path)

    # -------- Companies --------
    def list_companies(self) -> list[Company]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT company_id, name, created_at_ms, updated_at_ms FROM companies ORDER BY name ASC"
            ).fetchall()
            return [Company(*row) for row in rows]
        finally:
            conn.close()

    def get_company(self, company_id: int) -> Company | None:
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT company_id, name, created_at_ms, updated_at_ms FROM companies WHERE company_id = ?",
                (company_id,),
            ).fetchone()
            return Company(*row) if row else None
        finally:
            conn.close()

    def create_company(self, *, name: str, actor_user_id: str) -> Company:
        name = (name or "").strip()
        if not name:
            raise ValueError("公司名不能为空")

        now_ms = int(time.time() * 1000)
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO companies (name, created_at_ms, updated_at_ms) VALUES (?, ?, ?)",
                (name, now_ms, now_ms),
            )
            company_id = int(cur.lastrowid)
            self._log(
                conn,
                entity_type="company",
                action="create",
                entity_id=company_id,
                before_name=None,
                after_name=name,
                actor_user_id=actor_user_id,
            )
            conn.commit()
            return Company(company_id=company_id, name=name, created_at_ms=now_ms, updated_at_ms=now_ms)
        finally:
            conn.close()

    def update_company(self, *, company_id: int, name: str, actor_user_id: str) -> Company:
        name = (name or "").strip()
        if not name:
            raise ValueError("公司名不能为空")

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT company_id, name, created_at_ms, updated_at_ms FROM companies WHERE company_id = ?",
                (company_id,),
            ).fetchone()
            if not row:
                raise KeyError("公司不存在")
            before = Company(*row)

            now_ms = int(time.time() * 1000)
            cur.execute(
                "UPDATE companies SET name = ?, updated_at_ms = ? WHERE company_id = ?",
                (name, now_ms, company_id),
            )
            self._log(
                conn,
                entity_type="company",
                action="update",
                entity_id=company_id,
                before_name=before.name,
                after_name=name,
                actor_user_id=actor_user_id,
            )
            conn.commit()
            return Company(company_id=company_id, name=name, created_at_ms=before.created_at_ms, updated_at_ms=now_ms)
        finally:
            conn.close()

    def delete_company(self, *, company_id: int, actor_user_id: str) -> None:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT company_id, name, created_at_ms, updated_at_ms FROM companies WHERE company_id = ?",
                (company_id,),
            ).fetchone()
            if not row:
                raise KeyError("公司不存在")
            company = Company(*row)

            used = cur.execute("SELECT COUNT(*) FROM users WHERE company_id = ?", (company_id,)).fetchone()[0]
            if used and int(used) > 0:
                raise ValueError("该公司已被用户使用，无法删除")

            cur.execute("DELETE FROM companies WHERE company_id = ?", (company_id,))
            self._log(
                conn,
                entity_type="company",
                action="delete",
                entity_id=company_id,
                before_name=company.name,
                after_name=None,
                actor_user_id=actor_user_id,
            )
            conn.commit()
        finally:
            conn.close()

    # -------- Departments --------
    def list_departments(self) -> list[Department]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT department_id, name, created_at_ms, updated_at_ms FROM departments ORDER BY name ASC"
            ).fetchall()
            return [Department(*row) for row in rows]
        finally:
            conn.close()

    def get_department(self, department_id: int) -> Department | None:
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT department_id, name, created_at_ms, updated_at_ms FROM departments WHERE department_id = ?",
                (department_id,),
            ).fetchone()
            return Department(*row) if row else None
        finally:
            conn.close()

    def create_department(self, *, name: str, actor_user_id: str) -> Department:
        name = (name or "").strip()
        if not name:
            raise ValueError("部门名不能为空")

        now_ms = int(time.time() * 1000)
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO departments (name, created_at_ms, updated_at_ms) VALUES (?, ?, ?)",
                (name, now_ms, now_ms),
            )
            department_id = int(cur.lastrowid)
            self._log(
                conn,
                entity_type="department",
                action="create",
                entity_id=department_id,
                before_name=None,
                after_name=name,
                actor_user_id=actor_user_id,
            )
            conn.commit()
            return Department(department_id=department_id, name=name, created_at_ms=now_ms, updated_at_ms=now_ms)
        finally:
            conn.close()

    def update_department(self, *, department_id: int, name: str, actor_user_id: str) -> Department:
        name = (name or "").strip()
        if not name:
            raise ValueError("部门名不能为空")

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT department_id, name, created_at_ms, updated_at_ms FROM departments WHERE department_id = ?",
                (department_id,),
            ).fetchone()
            if not row:
                raise KeyError("部门不存在")
            before = Department(*row)

            now_ms = int(time.time() * 1000)
            cur.execute(
                "UPDATE departments SET name = ?, updated_at_ms = ? WHERE department_id = ?",
                (name, now_ms, department_id),
            )
            self._log(
                conn,
                entity_type="department",
                action="update",
                entity_id=department_id,
                before_name=before.name,
                after_name=name,
                actor_user_id=actor_user_id,
            )
            conn.commit()
            return Department(
                department_id=department_id, name=name, created_at_ms=before.created_at_ms, updated_at_ms=now_ms
            )
        finally:
            conn.close()

    def delete_department(self, *, department_id: int, actor_user_id: str) -> None:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT department_id, name, created_at_ms, updated_at_ms FROM departments WHERE department_id = ?",
                (department_id,),
            ).fetchone()
            if not row:
                raise KeyError("部门不存在")
            dept = Department(*row)

            used = cur.execute("SELECT COUNT(*) FROM users WHERE department_id = ?", (department_id,)).fetchone()[0]
            if used and int(used) > 0:
                raise ValueError("该部门已被用户使用，无法删除")

            cur.execute("DELETE FROM departments WHERE department_id = ?", (department_id,))
            self._log(
                conn,
                entity_type="department",
                action="delete",
                entity_id=department_id,
                before_name=dept.name,
                after_name=None,
                actor_user_id=actor_user_id,
            )
            conn.commit()
        finally:
            conn.close()

    # -------- Audit --------
    def list_audit_logs(
        self,
        *,
        entity_type: str | None = None,
        action: str | None = None,
        limit: int = 200,
    ) -> list[OrgDirectoryAuditLog]:
        limit = int(limit or 200)
        limit = max(1, min(limit, 1000))

        entity_type = (entity_type or "").strip() or None
        action = (action or "").strip() or None

        conn = self._get_connection()
        try:
            query = """
                SELECT id, entity_type, action, entity_id, before_name, after_name, actor_user_id, created_at_ms
                FROM org_directory_audit_logs
                WHERE 1=1
            """
            params: list[object] = []
            if entity_type:
                query += " AND entity_type = ?"
                params.append(entity_type)
            if action:
                query += " AND action = ?"
                params.append(action)
            query += " ORDER BY created_at_ms DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [OrgDirectoryAuditLog(*row) for row in rows]
        finally:
            conn.close()

    def _log(
        self,
        conn,
        *,
        entity_type: str,
        action: str,
        entity_id: int | None,
        before_name: str | None,
        after_name: str | None,
        actor_user_id: str,
    ) -> None:
        now_ms = int(time.time() * 1000)
        conn.execute(
            """
            INSERT INTO org_directory_audit_logs (
                entity_type, action, entity_id, before_name, after_name, actor_user_id, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (entity_type, action, entity_id, before_name, after_name, actor_user_id, now_ms),
        )

