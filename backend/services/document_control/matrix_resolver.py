from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


_KEY_FILE_SUBTYPE = "文件小类"
_KEY_COMPILER = "编制"
_KEY_SIGNOFF = "审核会签"
_KEY_APPROVER = "批准"
_KEY_REMARK = "备注"

_MARK_REQUIRED = "●"
_MARK_OPTIONAL = "○"

_POSITION_DIRECT_MANAGER = "编制人直接主管"
_POSITION_DOC_ADMIN = "文档管理员"
_POSITION_REGISTRATION = "注册"


@dataclass(slots=True)
class DocumentControlMatrixResolverError(Exception):
    code: str
    status_code: int = 409

    def __str__(self) -> str:
        return self.code


@dataclass(slots=True)
class MatrixApprover:
    user_id: str
    username: str | None = None
    full_name: str | None = None
    email: str | None = None
    employee_user_id: str | None = None
    source: str = "position"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MatrixPositionEvaluation:
    position_name: str
    step_kind: str
    mark: str
    member_source: str
    activation_rule: str
    included: bool
    skip_reason: str | None = None
    approvers: list[MatrixApprover] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["approvers"] = [item.as_dict() for item in self.approvers]
        return data


@dataclass(slots=True)
class CompilerCheckResult:
    position_name: str
    applicant_user_id: str
    matched: bool
    approvers: list[MatrixApprover] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["approvers"] = [item.as_dict() for item in self.approvers]
        return data


@dataclass(slots=True)
class MatrixResolutionResult:
    file_subtype: str
    document_type: str | None
    registration_ref: str | None
    compiler_check: CompilerCheckResult
    signoff_steps: list[MatrixPositionEvaluation] = field(default_factory=list)
    approval_steps: list[MatrixPositionEvaluation] = field(default_factory=list)
    snapshot: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "file_subtype": self.file_subtype,
            "document_type": self.document_type,
            "registration_ref": self.registration_ref,
            "compiler_check": self.compiler_check.as_dict(),
            "signoff_steps": [item.as_dict() for item in self.signoff_steps],
            "approval_steps": [item.as_dict() for item in self.approval_steps],
            "snapshot": self.snapshot,
        }


@dataclass(slots=True)
class DocumentApprovalMatrixEntry:
    file_subtype: str
    compiler_position: str
    signoff_marks: dict[str, str]
    approver_position: str
    remark: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DocumentApprovalMatrixEntry":
        if not isinstance(payload, dict):
            raise DocumentControlMatrixResolverError("document_control_matrix_entry_invalid", status_code=500)

        file_subtype = str(payload.get(_KEY_FILE_SUBTYPE) or "").strip()
        compiler_position = str(payload.get(_KEY_COMPILER) or "").strip()
        approver_position = str(payload.get(_KEY_APPROVER) or "").strip()
        signoff_marks = payload.get(_KEY_SIGNOFF)
        if _KEY_REMARK not in payload:
            raise DocumentControlMatrixResolverError("document_control_matrix_remark_missing", status_code=500)
        remark_value = payload.get(_KEY_REMARK)
        if not file_subtype:
            raise DocumentControlMatrixResolverError("document_control_matrix_file_subtype_invalid", status_code=500)
        if not compiler_position:
            raise DocumentControlMatrixResolverError("document_control_matrix_compiler_position_invalid", status_code=500)
        if not approver_position:
            raise DocumentControlMatrixResolverError("document_control_matrix_approver_position_invalid", status_code=500)
        if not isinstance(signoff_marks, dict):
            raise DocumentControlMatrixResolverError("document_control_matrix_signoff_invalid", status_code=500)
        if remark_value is not None and not isinstance(remark_value, str):
            raise DocumentControlMatrixResolverError("document_control_matrix_remark_invalid", status_code=500)
        normalized_marks = {
            str(key or "").strip(): str(value or "").strip()
            for key, value in signoff_marks.items()
            if str(key or "").strip()
        }
        return cls(
            file_subtype=file_subtype,
            compiler_position=compiler_position,
            signoff_marks=normalized_marks,
            approver_position=approver_position,
            remark=(str(remark_value or "").strip() or None),
        )


class DocumentControlMatrixResolver:
    def __init__(
        self,
        *,
        matrix_json_path: str | Path | None = None,
    ) -> None:
        self._matrix_json_path = (
            Path(matrix_json_path)
            if matrix_json_path is not None
            else Path(__file__).resolve().parents[3] / "docs" / "generated" / "document-approval-matrix.json"
        )

    def load_entries(self) -> list[DocumentApprovalMatrixEntry]:
        path = self._matrix_json_path
        if not path.exists():
            raise DocumentControlMatrixResolverError("document_control_matrix_missing", status_code=500)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise DocumentControlMatrixResolverError("document_control_matrix_invalid", status_code=500) from exc
        if not isinstance(payload, list):
            raise DocumentControlMatrixResolverError("document_control_matrix_invalid", status_code=500)
        return [DocumentApprovalMatrixEntry.from_dict(item) for item in payload]

    @staticmethod
    def build_position_assignment_index(positions: list[dict[str, Any]] | None) -> dict[str, list[MatrixApprover]]:
        index: dict[str, list[MatrixApprover]] = {}
        for item in positions or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            assigned_users = item.get("assigned_users") or []
            approvers = [
                MatrixApprover(
                    user_id=str(user.get("user_id") or "").strip(),
                    username=(str(user.get("username") or "").strip() or None),
                    full_name=(str(user.get("full_name") or "").strip() or None),
                    email=(str(user.get("email") or "").strip() or None),
                    employee_user_id=(str(user.get("employee_user_id") or "").strip() or None),
                    source="position",
                )
                for user in assigned_users
                if isinstance(user, dict) and str(user.get("user_id") or "").strip()
            ]
            index[name] = approvers
        return index

    def resolve(
        self,
        *,
        file_subtype: str,
        applicant_user_id: str,
        applicant_manager_user_id: str | None,
        document_type: str | None = None,
        registration_ref: str | None = None,
        usage_scope: str | None = None,
        position_assignments: dict[str, list[MatrixApprover | dict[str, Any]]] | list[dict[str, Any]] | None = None,
        matrix_entries: list[DocumentApprovalMatrixEntry] | None = None,
    ) -> MatrixResolutionResult:
        clean_file_subtype = str(file_subtype or "").strip()
        clean_applicant_user_id = str(applicant_user_id or "").strip()
        clean_manager_user_id = str(applicant_manager_user_id or "").strip() or None
        clean_document_type = str(document_type or "").strip() or None
        clean_registration_ref = str(registration_ref or "").strip() or None
        clean_usage_scope = str(usage_scope or "").strip() or None

        if not clean_file_subtype:
            raise DocumentControlMatrixResolverError("document_control_matrix_file_subtype_required", status_code=409)
        if not clean_applicant_user_id:
            raise DocumentControlMatrixResolverError("document_control_matrix_applicant_required", status_code=409)

        entries = matrix_entries or self.load_entries()
        entry = next((item for item in entries if item.file_subtype == clean_file_subtype), None)
        if entry is None:
            raise DocumentControlMatrixResolverError("document_control_matrix_file_subtype_not_found", status_code=409)

        if isinstance(position_assignments, list):
            assignment_index = self.build_position_assignment_index(position_assignments)
        else:
            assignment_index = self._normalize_assignment_mapping(position_assignments or {})

        compiler_approvers = self._resolve_position_approvers(
            position_name=entry.compiler_position,
            assignment_index=assignment_index,
            manager_user_id=clean_manager_user_id,
            registration_ref=clean_registration_ref,
            usage_scope=clean_usage_scope,
            row_remark=entry.remark,
            treat_as_optional=False,
        )
        compiler_check = CompilerCheckResult(
            position_name=entry.compiler_position,
            applicant_user_id=clean_applicant_user_id,
            matched=any(item.user_id == clean_applicant_user_id for item in compiler_approvers),
            approvers=compiler_approvers,
        )
        if not compiler_check.matched:
            raise DocumentControlMatrixResolverError("document_control_matrix_compiler_mismatch", status_code=409)

        signoff_steps: list[MatrixPositionEvaluation] = []
        signoff_snapshot: list[dict[str, Any]] = []
        for position_name, mark in entry.signoff_marks.items():
            evaluation = self._build_position_evaluation(
                step_kind="signoff",
                position_name=position_name,
                mark=mark,
                assignment_index=assignment_index,
                manager_user_id=clean_manager_user_id,
                registration_ref=clean_registration_ref,
                usage_scope=clean_usage_scope,
                row_remark=entry.remark,
            )
            signoff_snapshot.append(evaluation.as_dict())
            if evaluation.included:
                signoff_steps.append(evaluation)

        approval_evaluation = self._build_position_evaluation(
            step_kind="approval",
            position_name=entry.approver_position,
            mark=_MARK_REQUIRED,
            assignment_index=assignment_index,
            manager_user_id=clean_manager_user_id,
            registration_ref=clean_registration_ref,
            usage_scope=clean_usage_scope,
            row_remark=entry.remark,
        )
        approval_steps = [approval_evaluation] if approval_evaluation.included else []

        snapshot = {
            "file_subtype": clean_file_subtype,
            "document_type": clean_document_type,
            "registration_ref": clean_registration_ref,
            "usage_scope": clean_usage_scope,
            "remark": entry.remark,
            "compiler_check": compiler_check.as_dict(),
            "signoff_positions": signoff_snapshot,
            "approval_positions": [approval_evaluation.as_dict()],
        }

        return MatrixResolutionResult(
            file_subtype=clean_file_subtype,
            document_type=clean_document_type,
            registration_ref=clean_registration_ref,
            compiler_check=compiler_check,
            signoff_steps=signoff_steps,
            approval_steps=approval_steps,
            snapshot=snapshot,
        )

    def _build_position_evaluation(
        self,
        *,
        step_kind: str,
        position_name: str,
        mark: str,
        assignment_index: dict[str, list[MatrixApprover]],
        manager_user_id: str | None,
        registration_ref: str | None,
        usage_scope: str | None,
        row_remark: str | None,
    ) -> MatrixPositionEvaluation:
        clean_position = str(position_name or "").strip()
        clean_mark = str(mark or "").strip()
        activation_rule = self._activation_rule_for_position(clean_position, row_remark=row_remark)
        member_source = "direct_manager" if clean_position == _POSITION_DIRECT_MANAGER else "position"

        if clean_mark not in {_MARK_REQUIRED, _MARK_OPTIONAL}:
            return MatrixPositionEvaluation(
                position_name=clean_position,
                step_kind=step_kind,
                mark=clean_mark,
                member_source=member_source,
                activation_rule=activation_rule,
                included=False,
                skip_reason="blank_mark",
                approvers=[],
            )

        if clean_mark == _MARK_OPTIONAL:
            return MatrixPositionEvaluation(
                position_name=clean_position,
                step_kind=step_kind,
                mark=clean_mark,
                member_source=member_source,
                activation_rule=activation_rule,
                included=False,
                skip_reason="optional_mark",
                approvers=[],
            )

        if activation_rule == "registration_required" and not registration_ref:
            return MatrixPositionEvaluation(
                position_name=clean_position,
                step_kind=step_kind,
                mark=clean_mark or _MARK_REQUIRED,
                member_source=member_source,
                activation_rule=activation_rule,
                included=False,
                skip_reason="registration_ref_missing",
                approvers=[],
            )

        if activation_rule == "usage_scope_required" and not usage_scope:
            raise DocumentControlMatrixResolverError("document_control_matrix_usage_scope_required", status_code=409)

        approvers = self._resolve_position_approvers(
            position_name=clean_position,
            assignment_index=assignment_index,
            manager_user_id=manager_user_id,
            registration_ref=registration_ref,
            usage_scope=usage_scope,
            row_remark=row_remark,
            treat_as_optional=False,
        )
        return MatrixPositionEvaluation(
            position_name=clean_position,
            step_kind=step_kind,
            mark=clean_mark or _MARK_REQUIRED,
            member_source=member_source,
            activation_rule=activation_rule,
            included=True,
            approvers=approvers,
        )

    def _resolve_position_approvers(
        self,
        *,
        position_name: str,
        assignment_index: dict[str, list[MatrixApprover]],
        manager_user_id: str | None,
        registration_ref: str | None,  # noqa: ARG002
        usage_scope: str | None,  # noqa: ARG002
        row_remark: str | None,  # noqa: ARG002
        treat_as_optional: bool,
    ) -> list[MatrixApprover]:
        clean_position = str(position_name or "").strip()
        if clean_position == _POSITION_DIRECT_MANAGER:
            if not manager_user_id:
                if treat_as_optional:
                    return []
                raise DocumentControlMatrixResolverError("document_control_matrix_direct_manager_missing", status_code=409)
            return [MatrixApprover(user_id=manager_user_id, source="direct_manager")]

        variants = self._position_name_variants(clean_position)
        matched_variant_names = [name for name in variants if name in assignment_index]
        if not matched_variant_names:
            if treat_as_optional:
                return []
            raise DocumentControlMatrixResolverError(
                f"document_control_matrix_position_missing:{clean_position}",
                status_code=409,
            )
        approvers = self._merge_position_approvers(
            assignment_index=assignment_index,
            variant_names=matched_variant_names,
        )
        if not approvers:
            if treat_as_optional:
                return []
            raise DocumentControlMatrixResolverError(
                f"document_control_matrix_position_unassigned:{clean_position}",
                status_code=409,
            )
        return approvers

    @staticmethod
    def _normalize_assignment_mapping(
        mapping: dict[str, list[MatrixApprover | dict[str, Any]]]
    ) -> dict[str, list[MatrixApprover]]:
        index: dict[str, list[MatrixApprover]] = {}
        for raw_name, raw_users in (mapping or {}).items():
            name = str(raw_name or "").strip()
            if not name:
                continue
            approvers: list[MatrixApprover] = []
            for item in raw_users or []:
                if isinstance(item, MatrixApprover):
                    approvers.append(item)
                    continue
                if not isinstance(item, dict):
                    continue
                user_id = str(item.get("user_id") or "").strip()
                if not user_id:
                    continue
                approvers.append(
                    MatrixApprover(
                        user_id=user_id,
                        username=(str(item.get("username") or "").strip() or None),
                        full_name=(str(item.get("full_name") or "").strip() or None),
                        email=(str(item.get("email") or "").strip() or None),
                        employee_user_id=(str(item.get("employee_user_id") or "").strip() or None),
                        source=str(item.get("source") or "position"),
                    )
                )
            index[name] = approvers
        return index

    @staticmethod
    def _activation_rule_for_position(position_name: str, *, row_remark: str | None = None) -> str:
        if str(position_name or "").strip() == _POSITION_REGISTRATION:
            return "registration_required"
        if "根据使用区域" in str(row_remark or ""):
            return "usage_scope_required"
        return "always"

    @staticmethod
    def _position_name_variants(position_name: str) -> list[str]:
        raw = str(position_name or "").strip()
        if not raw:
            return []
        variants: list[str] = [raw]
        normalized = raw.replace("/或", "或").replace("/", "或")
        parts = [item.strip() for item in re.split(r"\s*或\s*", normalized) if item.strip()]
        for item in parts:
            if item not in variants:
                variants.append(item)
        return variants

    @staticmethod
    def _merge_position_approvers(
        *,
        assignment_index: dict[str, list[MatrixApprover]],
        variant_names: list[str],
    ) -> list[MatrixApprover]:
        merged: list[MatrixApprover] = []
        seen_user_ids: set[str] = set()
        for variant_name in variant_names:
            for approver in assignment_index.get(variant_name) or []:
                if approver.user_id in seen_user_ids:
                    continue
                merged.append(approver)
                seen_user_ids.add(approver.user_id)
        return merged
