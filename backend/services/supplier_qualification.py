from __future__ import annotations

from datetime import date
import time
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


class SupplierQualificationError(Exception):
    def __init__(self, code: str, *, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


COMPONENT_CATEGORIES = {
    "vendor_service",
    "off_the_shelf_software",
    "database",
    "infrastructure",
    "interface",
}
DEPLOYMENT_SCOPES = {"shared_service", "tenant_database", "server", "workstation"}
SUPPLIER_APPROVAL_STATUSES = {"pending_review", "approved", "conditional", "rejected"}
QUALIFICATION_PHASE_STATUSES = {"passed", "failed", "not_applicable"}


class SupplierQualificationService:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _require_text(value: Any, field_name: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise SupplierQualificationError(f"{field_name}_required", status_code=400)
        return text

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _require_known_value(value: Any, *, field_name: str, allowed: set[str]) -> str:
        text = str(value or "").strip().lower()
        if text not in allowed:
            raise SupplierQualificationError(f"invalid_{field_name}", status_code=400)
        return text

    @staticmethod
    def _validate_iso_date(value: str | None, *, field_name: str) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            date.fromisoformat(text)
        except ValueError as exc:
            raise SupplierQualificationError(f"invalid_{field_name}", status_code=400) from exc
        return text

    @staticmethod
    def _derive_component_status(*, supplier_approval_status: str, approved_version: str | None, current_version: str) -> str:
        if supplier_approval_status == "rejected":
            return "rejected"
        if approved_version is None:
            return "pending_review"
        if approved_version != current_version:
            return "requalification_required"
        if supplier_approval_status == "approved":
            return "approved"
        return "pending_review"

    @staticmethod
    def _derive_environment_status(*, iq_status: str, oq_status: str, pq_status: str) -> str:
        if iq_status == oq_status == pq_status == "passed":
            return "approved"
        return "rework_required"

    @staticmethod
    def _serialize_component(row) -> dict[str, Any]:
        return {
            "component_code": str(row["component_code"]),
            "component_name": str(row["component_name"]),
            "supplier_name": str(row["supplier_name"]),
            "component_category": str(row["component_category"]),
            "deployment_scope": str(row["deployment_scope"]),
            "current_version": str(row["current_version"]),
            "approved_version": (str(row["approved_version"]) if row["approved_version"] else None),
            "supplier_approval_status": str(row["supplier_approval_status"]),
            "qualification_status": str(row["qualification_status"]),
            "intended_use_summary": str(row["intended_use_summary"]),
            "qualification_summary": str(row["qualification_summary"]),
            "supplier_audit_summary": str(row["supplier_audit_summary"]),
            "known_issue_review": str(row["known_issue_review"]),
            "revalidation_trigger": (str(row["revalidation_trigger"]) if row["revalidation_trigger"] else None),
            "migration_plan_summary": str(row["migration_plan_summary"]),
            "review_due_date": (str(row["review_due_date"]) if row["review_due_date"] else None),
            "approved_by_user_id": (str(row["approved_by_user_id"]) if row["approved_by_user_id"] else None),
            "approved_at_ms": (int(row["approved_at_ms"]) if row["approved_at_ms"] is not None else None),
            "created_at_ms": int(row["created_at_ms"] or 0),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
        }

    @staticmethod
    def _serialize_environment_record(row) -> dict[str, Any]:
        return {
            "record_id": str(row["record_id"]),
            "component_code": str(row["component_code"]),
            "environment_name": str(row["environment_name"]),
            "company_id": (int(row["company_id"]) if row["company_id"] is not None else None),
            "release_version": str(row["release_version"]),
            "protocol_ref": str(row["protocol_ref"]),
            "iq_status": str(row["iq_status"]),
            "oq_status": str(row["oq_status"]),
            "pq_status": str(row["pq_status"]),
            "qualification_status": str(row["qualification_status"]),
            "qualification_summary": str(row["qualification_summary"]),
            "deviation_summary": (str(row["deviation_summary"]) if row["deviation_summary"] else None),
            "executed_by_user_id": str(row["executed_by_user_id"]),
            "approved_by_user_id": (str(row["approved_by_user_id"]) if row["approved_by_user_id"] else None),
            "executed_at_ms": int(row["executed_at_ms"] or 0),
            "approved_at_ms": (int(row["approved_at_ms"]) if row["approved_at_ms"] is not None else None),
            "created_at_ms": int(row["created_at_ms"] or 0),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
        }

    def get_component(self, component_code: str) -> dict[str, Any]:
        component_code = self._require_text(component_code, "component_code")
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT
                    component_code,
                    component_name,
                    supplier_name,
                    component_category,
                    deployment_scope,
                    current_version,
                    approved_version,
                    supplier_approval_status,
                    qualification_status,
                    intended_use_summary,
                    qualification_summary,
                    supplier_audit_summary,
                    known_issue_review,
                    revalidation_trigger,
                    migration_plan_summary,
                    review_due_date,
                    approved_by_user_id,
                    approved_at_ms,
                    created_at_ms,
                    updated_at_ms
                FROM supplier_component_qualifications
                WHERE component_code = ?
                """,
                (component_code,),
            ).fetchone()
            if row is None:
                raise SupplierQualificationError("supplier_component_not_found", status_code=404)
            return self._serialize_component(row)
        finally:
            conn.close()

    def list_components(self, *, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 100), 200))
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT component_code
                FROM supplier_component_qualifications
                ORDER BY updated_at_ms DESC, component_code ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            conn.close()
        return [self.get_component(str(row["component_code"])) for row in rows]

    def upsert_component(
        self,
        *,
        component_code: str,
        component_name: str,
        supplier_name: str,
        component_category: str,
        deployment_scope: str,
        current_version: str,
        approved_version: str | None,
        supplier_approval_status: str,
        intended_use_summary: str,
        qualification_summary: str,
        supplier_audit_summary: str,
        known_issue_review: str,
        revalidation_trigger: str | None,
        migration_plan_summary: str,
        review_due_date: str | None,
        approved_by_user_id: str | None,
    ) -> dict[str, Any]:
        component_code = self._require_text(component_code, "component_code")
        component_name = self._require_text(component_name, "component_name")
        supplier_name = self._require_text(supplier_name, "supplier_name")
        component_category = self._require_known_value(
            component_category,
            field_name="component_category",
            allowed=COMPONENT_CATEGORIES,
        )
        deployment_scope = self._require_known_value(
            deployment_scope,
            field_name="deployment_scope",
            allowed=DEPLOYMENT_SCOPES,
        )
        current_version = self._require_text(current_version, "current_version")
        approved_version = self._optional_text(approved_version)
        supplier_approval_status = self._require_known_value(
            supplier_approval_status,
            field_name="supplier_approval_status",
            allowed=SUPPLIER_APPROVAL_STATUSES,
        )
        intended_use_summary = self._require_text(intended_use_summary, "intended_use_summary")
        qualification_summary = self._require_text(qualification_summary, "qualification_summary")
        supplier_audit_summary = self._require_text(supplier_audit_summary, "supplier_audit_summary")
        known_issue_review = self._require_text(known_issue_review, "known_issue_review")
        revalidation_trigger = self._optional_text(revalidation_trigger)
        migration_plan_summary = self._require_text(migration_plan_summary, "migration_plan_summary")
        review_due_date = self._validate_iso_date(review_due_date, field_name="review_due_date")
        approved_by_user_id = self._optional_text(approved_by_user_id)

        qualification_status = self._derive_component_status(
            supplier_approval_status=supplier_approval_status,
            approved_version=approved_version,
            current_version=current_version,
        )
        now_ms = int(time.time() * 1000)
        approved_at_ms = now_ms if qualification_status == "approved" and approved_by_user_id else None

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT component_code FROM supplier_component_qualifications WHERE component_code = ?",
                (component_code,),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO supplier_component_qualifications (
                        component_code,
                        component_name,
                        supplier_name,
                        component_category,
                        deployment_scope,
                        current_version,
                        approved_version,
                        supplier_approval_status,
                        qualification_status,
                        intended_use_summary,
                        qualification_summary,
                        supplier_audit_summary,
                        known_issue_review,
                        revalidation_trigger,
                        migration_plan_summary,
                        review_due_date,
                        approved_by_user_id,
                        approved_at_ms,
                        created_at_ms,
                        updated_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        component_code,
                        component_name,
                        supplier_name,
                        component_category,
                        deployment_scope,
                        current_version,
                        approved_version,
                        supplier_approval_status,
                        qualification_status,
                        intended_use_summary,
                        qualification_summary,
                        supplier_audit_summary,
                        known_issue_review,
                        revalidation_trigger,
                        migration_plan_summary,
                        review_due_date,
                        approved_by_user_id,
                        approved_at_ms,
                        now_ms,
                        now_ms,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE supplier_component_qualifications
                    SET component_name = ?,
                        supplier_name = ?,
                        component_category = ?,
                        deployment_scope = ?,
                        current_version = ?,
                        approved_version = ?,
                        supplier_approval_status = ?,
                        qualification_status = ?,
                        intended_use_summary = ?,
                        qualification_summary = ?,
                        supplier_audit_summary = ?,
                        known_issue_review = ?,
                        revalidation_trigger = ?,
                        migration_plan_summary = ?,
                        review_due_date = ?,
                        approved_by_user_id = ?,
                        approved_at_ms = ?,
                        updated_at_ms = ?
                    WHERE component_code = ?
                    """,
                    (
                        component_name,
                        supplier_name,
                        component_category,
                        deployment_scope,
                        current_version,
                        approved_version,
                        supplier_approval_status,
                        qualification_status,
                        intended_use_summary,
                        qualification_summary,
                        supplier_audit_summary,
                        known_issue_review,
                        revalidation_trigger,
                        migration_plan_summary,
                        review_due_date,
                        approved_by_user_id,
                        approved_at_ms,
                        now_ms,
                        component_code,
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_component(component_code)

    def record_version_change(
        self,
        *,
        component_code: str,
        new_version: str,
        change_summary: str,
    ) -> dict[str, Any]:
        component = self.get_component(component_code)
        new_version = self._require_text(new_version, "new_version")
        change_summary = self._require_text(change_summary, "change_summary")
        if component["current_version"] == new_version:
            raise SupplierQualificationError("component_version_unchanged", status_code=409)
        return self.upsert_component(
            component_code=component["component_code"],
            component_name=component["component_name"],
            supplier_name=component["supplier_name"],
            component_category=component["component_category"],
            deployment_scope=component["deployment_scope"],
            current_version=new_version,
            approved_version=component["approved_version"],
            supplier_approval_status=component["supplier_approval_status"],
            intended_use_summary=component["intended_use_summary"],
            qualification_summary=component["qualification_summary"],
            supplier_audit_summary=component["supplier_audit_summary"],
            known_issue_review=component["known_issue_review"],
            revalidation_trigger=change_summary,
            migration_plan_summary=component["migration_plan_summary"],
            review_due_date=component["review_due_date"],
            approved_by_user_id=component["approved_by_user_id"],
        )

    def get_environment_record(self, record_id: str) -> dict[str, Any]:
        record_id = self._require_text(record_id, "record_id")
        conn = self._conn()
        try:
            row = conn.execute(
                """
                SELECT
                    record_id,
                    component_code,
                    environment_name,
                    company_id,
                    release_version,
                    protocol_ref,
                    iq_status,
                    oq_status,
                    pq_status,
                    qualification_status,
                    qualification_summary,
                    deviation_summary,
                    executed_by_user_id,
                    approved_by_user_id,
                    executed_at_ms,
                    approved_at_ms,
                    created_at_ms,
                    updated_at_ms
                FROM environment_qualification_records
                WHERE record_id = ?
                """,
                (record_id,),
            ).fetchone()
            if row is None:
                raise SupplierQualificationError("environment_qualification_not_found", status_code=404)
            return self._serialize_environment_record(row)
        finally:
            conn.close()

    def list_environment_records(
        self,
        *,
        limit: int = 100,
        component_code: str | None = None,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 100), 200))
        conn = self._conn()
        try:
            if component_code:
                rows = conn.execute(
                    """
                    SELECT record_id
                    FROM environment_qualification_records
                    WHERE component_code = ?
                    ORDER BY executed_at_ms DESC, record_id DESC
                    LIMIT ?
                    """,
                    (str(component_code).strip(), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT record_id
                    FROM environment_qualification_records
                    ORDER BY executed_at_ms DESC, record_id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        finally:
            conn.close()
        return [self.get_environment_record(str(row["record_id"])) for row in rows]

    def record_environment_qualification(
        self,
        *,
        component_code: str,
        environment_name: str,
        company_id: int | None,
        release_version: str,
        protocol_ref: str,
        iq_status: str,
        oq_status: str,
        pq_status: str,
        qualification_summary: str,
        deviation_summary: str | None,
        executed_by_user_id: str,
        approved_by_user_id: str | None,
    ) -> dict[str, Any]:
        component = self.get_component(component_code)
        environment_name = self._require_text(environment_name, "environment_name")
        release_version = self._require_text(release_version, "release_version")
        protocol_ref = self._require_text(protocol_ref, "protocol_ref")
        iq_status = self._require_known_value(iq_status, field_name="iq_status", allowed=QUALIFICATION_PHASE_STATUSES)
        oq_status = self._require_known_value(oq_status, field_name="oq_status", allowed=QUALIFICATION_PHASE_STATUSES)
        pq_status = self._require_known_value(pq_status, field_name="pq_status", allowed=QUALIFICATION_PHASE_STATUSES)
        qualification_summary = self._require_text(qualification_summary, "qualification_summary")
        deviation_summary = self._optional_text(deviation_summary)
        executed_by_user_id = self._require_text(executed_by_user_id, "executed_by_user_id")
        approved_by_user_id = self._optional_text(approved_by_user_id)

        if component["deployment_scope"] == "tenant_database" and company_id is None:
            raise SupplierQualificationError("tenant_company_id_required", status_code=400)
        if component["qualification_status"] != "approved":
            raise SupplierQualificationError("supplier_component_requires_requalification", status_code=409)

        qualification_status = self._derive_environment_status(
            iq_status=iq_status,
            oq_status=oq_status,
            pq_status=pq_status,
        )
        now_ms = int(time.time() * 1000)
        approved_at_ms = now_ms if qualification_status == "approved" and approved_by_user_id else None
        record_id = str(uuid4())

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO environment_qualification_records (
                    record_id,
                    component_code,
                    environment_name,
                    company_id,
                    release_version,
                    protocol_ref,
                    iq_status,
                    oq_status,
                    pq_status,
                    qualification_status,
                    qualification_summary,
                    deviation_summary,
                    executed_by_user_id,
                    approved_by_user_id,
                    executed_at_ms,
                    approved_at_ms,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    component["component_code"],
                    environment_name,
                    int(company_id) if company_id is not None else None,
                    release_version,
                    protocol_ref,
                    iq_status,
                    oq_status,
                    pq_status,
                    qualification_status,
                    qualification_summary,
                    deviation_summary,
                    executed_by_user_id,
                    approved_by_user_id,
                    now_ms,
                    approved_at_ms,
                    now_ms,
                    now_ms,
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_environment_record(record_id)
