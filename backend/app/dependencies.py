from dataclasses import dataclass
from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.tenant_paths import normalize_company_id, resolve_tenant_auth_db_path
from backend.database.schema_migrations import ensure_schema
from backend.services.chat_session_store import ChatSessionStore
from backend.services.auth_session_store import AuthSessionStore
from backend.services.data_security import DataSecurityStore
from backend.services.audit_log_store import AuditLogStore
from backend.services.chat_message_sources_store import ChatMessageSourcesStore
from backend.services.deletion_log_store import DeletionLogStore
from backend.services.download_log_store import DownloadLogStore
from backend.services.kb_store import KbStore
from backend.services.knowledge_directory_store import KnowledgeDirectoryStore
from backend.services.permission_group_store import PermissionGroupStore
from backend.services.permission_group_folder_store import PermissionGroupFolderManager, PermissionGroupFolderStore
from backend.services.patent_download.store import PatentDownloadStore
from backend.services.paper_download.store import PaperDownloadStore
from backend.services.package_drawing.store import PackageDrawingStore
from backend.services.ragflow_connection import create_ragflow_connection
from backend.services.ragflow_chat_service import RagflowChatService
from backend.services.ragflow_service import RagflowService
from backend.services.org_directory_store import OrgDirectoryStore
from backend.services.user_store import UserStore
from backend.services.search_config_store import SearchConfigStore
from backend.services.upload_settings_store import UploadSettingsStore
from backend.services.audit import AuditLogManager
from backend.services.auth_session import AuthSessionManager
from backend.services.approval import ApprovalWorkflowService, ApprovalWorkflowStore
from backend.services.knowledge_ingestion import KnowledgeIngestionManager
from backend.services.knowledge_management import KnowledgeManagementManager
from backend.services.knowledge_tree import KnowledgeTreeManager
from backend.services.notification import NotificationManager, NotificationStore
from backend.services.electronic_signature import ElectronicSignatureService, ElectronicSignatureStore
from backend.services.inbox_store import UserInboxStore
from backend.services.inbox_service import UserInboxService
from backend.services.operation_approval import OperationApprovalService, OperationApprovalStore
from backend.services.emergency_change import EmergencyChangeService
from backend.services.supplier_qualification import SupplierQualificationService
from backend.services.training_compliance import TrainingComplianceService
from backend.services.watermark_policy_store import WatermarkPolicyStore
from backend.app.core.config import settings


@dataclass
class AppDependencies:
    user_store: UserStore
    kb_store: KbStore
    ragflow_service: RagflowService
    deletion_log_store: DeletionLogStore
    download_log_store: DownloadLogStore
    audit_log_store: AuditLogStore
    audit_log_manager: AuditLogManager
    ragflow_chat_service: RagflowChatService
    chat_session_store: ChatSessionStore
    auth_session_store: AuthSessionStore
    auth_session_manager: AuthSessionManager
    chat_message_sources_store: ChatMessageSourcesStore
    permission_group_store: PermissionGroupStore
    org_directory_store: OrgDirectoryStore
    data_security_store: DataSecurityStore
    search_config_store: SearchConfigStore
    upload_settings_store: UploadSettingsStore
    patent_download_store: PatentDownloadStore
    paper_download_store: PaperDownloadStore
    package_drawing_store: PackageDrawingStore
    knowledge_directory_store: KnowledgeDirectoryStore
    knowledge_directory_manager: KnowledgeTreeManager
    knowledge_tree_manager: KnowledgeTreeManager
    knowledge_management_manager: KnowledgeManagementManager
    knowledge_ingestion_manager: KnowledgeIngestionManager | None
    permission_group_folder_store: PermissionGroupFolderStore
    permission_group_folder_manager: PermissionGroupFolderManager
    approval_workflow_service: ApprovalWorkflowService | None = None
    electronic_signature_store: ElectronicSignatureStore | None = None
    electronic_signature_service: ElectronicSignatureService | None = None
    emergency_change_service: EmergencyChangeService | None = None
    supplier_qualification_service: SupplierQualificationService | None = None
    training_compliance_service: TrainingComplianceService | None = None
    notification_manager: NotificationManager | None = None
    notification_service: NotificationManager | None = None
    user_inbox_store: UserInboxStore | None = None
    user_inbox_service: UserInboxService | None = None
    operation_approval_service: OperationApprovalService | None = None
    watermark_policy_store: WatermarkPolicyStore | None = None


def create_dependencies(db_path: str | None = None) -> AppDependencies:
    db_path = resolve_auth_db_path(db_path)

    ensure_schema(str(db_path))

    chat_session_store = ChatSessionStore(db_path=str(db_path))
    auth_session_store = AuthSessionStore(db_path=str(db_path))
    auth_session_manager = AuthSessionManager(port=auth_session_store)
    ragflow_conn = create_ragflow_connection()
    ragflow_service = RagflowService(connection=ragflow_conn)
    data_security_store = DataSecurityStore(db_path=str(db_path))
    chat_message_sources_store = ChatMessageSourcesStore(db_path=str(db_path))
    search_config_store = SearchConfigStore(db_path=str(db_path))
    knowledge_directory_store = KnowledgeDirectoryStore(db_path=str(db_path))
    knowledge_tree_manager = KnowledgeTreeManager(store=knowledge_directory_store)
    knowledge_directory_manager = knowledge_tree_manager
    knowledge_management_manager = KnowledgeManagementManager(
        tree_manager=knowledge_tree_manager,
        directory_store=knowledge_directory_store,
        ragflow_service=ragflow_service,
    )
    permission_group_folder_store = PermissionGroupFolderStore(db_path=str(db_path))
    permission_group_folder_manager = PermissionGroupFolderManager(store=permission_group_folder_store)
    notification_store = NotificationStore(db_path=str(db_path))
    user_inbox_store = UserInboxStore(db_path=str(db_path))
    electronic_signature_store = ElectronicSignatureStore(db_path=str(db_path))
    emergency_change_service = EmergencyChangeService(db_path=str(db_path))
    supplier_qualification_service = SupplierQualificationService(db_path=str(db_path))
    training_compliance_service = TrainingComplianceService(db_path=str(db_path))
    watermark_policy_store = WatermarkPolicyStore(db_path=str(db_path))
    user_store = UserStore(db_path=str(db_path))
    audit_log_store = AuditLogStore(db_path=str(db_path))
    audit_log_manager = AuditLogManager(store=audit_log_store)
    notification_manager = NotificationManager(
        store=notification_store,
        audit_log_manager=audit_log_manager,
        retry_interval_seconds=int(settings.NOTIFICATION_RETRY_INTERVAL_SECONDS or 60),
    )
    user_inbox_service = UserInboxService(store=user_inbox_store)
    approval_workflow_service = ApprovalWorkflowService(
        store=ApprovalWorkflowStore(db_path=str(db_path)),
        notification_manager=notification_manager,
        user_store=user_store,
    )
    electronic_signature_service = ElectronicSignatureService(store=electronic_signature_store)

    deps = AppDependencies(
        user_store=user_store,
        kb_store=KbStore(db_path=str(db_path)),
        ragflow_service=ragflow_service,
        deletion_log_store=DeletionLogStore(db_path=str(db_path)),
        download_log_store=DownloadLogStore(db_path=str(db_path)),
        audit_log_store=audit_log_store,
        audit_log_manager=audit_log_manager,
        ragflow_chat_service=RagflowChatService(session_store=chat_session_store, connection=ragflow_conn),
        chat_session_store=chat_session_store,
        auth_session_store=auth_session_store,
        auth_session_manager=auth_session_manager,
        chat_message_sources_store=chat_message_sources_store,
        permission_group_store=PermissionGroupStore(database_path=str(db_path)),
        org_directory_store=OrgDirectoryStore(db_path=str(db_path)),
        data_security_store=data_security_store,
        search_config_store=search_config_store,
        upload_settings_store=UploadSettingsStore(db_path=str(db_path)),
        patent_download_store=PatentDownloadStore(db_path=str(db_path)),
        paper_download_store=PaperDownloadStore(db_path=str(db_path)),
        package_drawing_store=PackageDrawingStore(db_path=str(db_path)),
        knowledge_directory_store=knowledge_directory_store,
        knowledge_directory_manager=knowledge_directory_manager,
        knowledge_tree_manager=knowledge_tree_manager,
        knowledge_management_manager=knowledge_management_manager,
        knowledge_ingestion_manager=None,
        permission_group_folder_store=permission_group_folder_store,
        permission_group_folder_manager=permission_group_folder_manager,
        approval_workflow_service=approval_workflow_service,
        electronic_signature_store=electronic_signature_store,
        electronic_signature_service=electronic_signature_service,
        emergency_change_service=emergency_change_service,
        supplier_qualification_service=supplier_qualification_service,
        training_compliance_service=training_compliance_service,
        notification_manager=notification_manager,
        notification_service=notification_manager,
        user_inbox_store=user_inbox_store,
        user_inbox_service=user_inbox_service,
        operation_approval_service=None,
        watermark_policy_store=watermark_policy_store,
    )
    deps.operation_approval_service = OperationApprovalService(
        store=OperationApprovalStore(db_path=str(db_path)),
        user_store=user_store,
        inbox_service=user_inbox_service,
        notification_service=notification_manager,
        electronic_signature_service=electronic_signature_service,
        deps=deps,
    )
    deps.knowledge_ingestion_manager = KnowledgeIngestionManager(deps=deps)
    return deps


def _ensure_tenant_deps_cache(app: Any) -> dict[int, AppDependencies]:
    cache = getattr(getattr(app, "state", None), "tenant_deps_cache", None)
    if isinstance(cache, dict):
        return cache
    cache = {}
    app.state.tenant_deps_cache = cache
    return cache


def get_global_dependencies(app: Any) -> AppDependencies:
    deps = getattr(getattr(app, "state", None), "deps", None)
    if deps is None:
        raise RuntimeError("app_dependencies_not_initialized")
    return deps


def get_tenant_dependencies(app: Any, *, company_id: int | str) -> AppDependencies:
    cid = normalize_company_id(company_id)
    cache = _ensure_tenant_deps_cache(app)
    cached = cache.get(cid)
    if cached is not None:
        return cached

    base_db_path = getattr(getattr(app, "state", None), "base_auth_db_path", None)
    tenant_db_path = resolve_tenant_auth_db_path(company_id=cid, base_db_path=base_db_path)
    deps = create_dependencies(db_path=str(tenant_db_path))
    cache[cid] = deps
    return deps
