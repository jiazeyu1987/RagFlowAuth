from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from backend.app.core.config import settings
from backend.database.paths import resolve_auth_db_path
from backend.database.schema.ensure import ensure_schema
from backend.database.sqlite import connect_sqlite
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.auth_session import AuthSessionManager
from backend.services.auth_session_store import AuthSessionStore
from backend.services.chat_management import ChatManagementManager, ChatOwnershipStore
from backend.services.chat_message_sources_store import ChatMessageSourcesStore
from backend.services.chat_session_store import ChatSessionStore
from backend.services.data_security.store import DataSecurityStore
from backend.services.deletion_log_store import DeletionLogStore
from backend.services.download_log_store import DownloadLogStore
from backend.services.electronic_signature import ElectronicSignatureService, ElectronicSignatureStore
from backend.services.emergency_change import EmergencyChangeService
from backend.services.inbox_service import UserInboxService
from backend.services.inbox_store import UserInboxStore
from backend.services.kb.store import KbStore
from backend.services.knowledge_directory.store import KnowledgeDirectoryStore
from backend.services.knowledge_ingestion import KnowledgeIngestionManager
from backend.services.knowledge_management import KnowledgeManagementManager
from backend.services.knowledge_tree import KnowledgeTreeManager
from backend.services.notification import NotificationManager, NotificationStore
from backend.services.operation_approval import OperationApprovalService, OperationApprovalStore
from backend.services.org_directory_store import OrgDirectoryStore, OrgStructureManager
from backend.services.package_drawing.store import PackageDrawingStore
from backend.services.paper_download.store import PaperDownloadStore
from backend.services.patent_download.store import PatentDownloadStore
from backend.services.permission_group_folders.manager import PermissionGroupFolderManager
from backend.services.permission_group_folders.store import PermissionGroupFolderStore
from backend.services.permission_groups.store import PermissionGroupStore
from backend.services.ragflow_chat_service import RagflowChatService
from backend.services.ragflow_connection import create_ragflow_connection
from backend.services.ragflow_service import RagflowService
from backend.services.search_config_store import SearchConfigStore
from backend.services.supplier_qualification import SupplierQualificationService
from backend.services.training_compliance import TrainingComplianceService
from backend.services.upload_settings_store import UploadSettingsStore
from backend.services.users.store import UserStore
from backend.services.users.tool_permission_store import UserToolPermissionStore
from backend.services.watermark_policy_store import WatermarkPolicyStore


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
    user_tool_permission_store: UserToolPermissionStore
    org_directory_store: OrgDirectoryStore
    org_structure_manager: OrgStructureManager
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
    chat_management_manager: ChatManagementManager | None = None
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


@dataclass(frozen=True)
class DependencyBuildConfig:
    db_path: str | None = None
    operation_approval_control_db_path: str | None = None
    training_compliance_db_path: str | None = None
    operation_approval_execution_deps_resolver: Callable[[int | str], AppDependencies] | None = None


@dataclass(frozen=True)
class _DependencyDbPaths:
    auth_db_path: Any
    operation_approval_db_path: Any
    training_db_path: Any

    @property
    def inbox_db_path(self) -> Any:
        return self.operation_approval_db_path


@dataclass(frozen=True)
class _OperationApprovalDependencySet:
    user_store: UserStore
    notification_service: NotificationManager | None
    external_notification_service: NotificationManager | None
    inbox_service: UserInboxService | None
    electronic_signature_service: ElectronicSignatureService | None


@dataclass(frozen=True)
class _SharedRuntime:
    chat_session_store: ChatSessionStore
    chat_ownership_store: ChatOwnershipStore
    auth_session_store: AuthSessionStore
    auth_session_manager: AuthSessionManager
    ragflow_service: RagflowService
    ragflow_chat_service: RagflowChatService
    data_security_store: DataSecurityStore
    chat_message_sources_store: ChatMessageSourcesStore
    search_config_store: SearchConfigStore
    knowledge_directory_store: KnowledgeDirectoryStore
    knowledge_tree_manager: KnowledgeTreeManager
    knowledge_management_manager: KnowledgeManagementManager
    chat_management_manager: ChatManagementManager
    permission_group_folder_store: PermissionGroupFolderStore
    permission_group_folder_manager: PermissionGroupFolderManager
    electronic_signature_store: ElectronicSignatureStore
    electronic_signature_service: ElectronicSignatureService
    emergency_change_service: EmergencyChangeService
    supplier_qualification_service: SupplierQualificationService
    training_compliance_service: TrainingComplianceService
    watermark_policy_store: WatermarkPolicyStore
    user_store: UserStore
    kb_store: KbStore
    deletion_log_store: DeletionLogStore
    download_log_store: DownloadLogStore
    audit_log_store: AuditLogStore
    audit_log_manager: AuditLogManager
    org_directory_store: OrgDirectoryStore
    org_structure_manager: OrgStructureManager
    permission_group_store: PermissionGroupStore
    user_tool_permission_store: UserToolPermissionStore
    upload_settings_store: UploadSettingsStore
    patent_download_store: PatentDownloadStore
    paper_download_store: PaperDownloadStore
    package_drawing_store: PackageDrawingStore
    notification_manager: NotificationManager
    user_inbox_store: UserInboxStore
    user_inbox_service: UserInboxService


def _ensure_default_notification_channels(notification_manager: NotificationManager | None) -> None:
    if notification_manager is None:
        return
    existing = notification_manager.list_channels(enabled_only=False)
    has_in_app = any(str(item.get("channel_type") or "").strip().lower() == "in_app" for item in existing)
    if has_in_app:
        return
    notification_manager.upsert_channel(
        channel_id="inapp-main",
        channel_type="in_app",
        name="\u7ad9\u5185\u4fe1",
        enabled=True,
        config={},
    )


def resolve_dependency_db_paths(config: DependencyBuildConfig) -> _DependencyDbPaths:
    auth_db_path = resolve_auth_db_path(config.db_path)
    operation_approval_db_path = (
        resolve_auth_db_path(config.operation_approval_control_db_path)
        if config.operation_approval_control_db_path is not None
        else auth_db_path
    )
    training_db_path = (
        resolve_auth_db_path(config.training_compliance_db_path)
        if config.training_compliance_db_path is not None
        else auth_db_path
    )
    return _DependencyDbPaths(
        auth_db_path=auth_db_path,
        operation_approval_db_path=operation_approval_db_path,
        training_db_path=training_db_path,
    )


def ensure_dependency_schemas(paths: _DependencyDbPaths) -> None:
    ensure_schema(str(paths.auth_db_path))
    if paths.operation_approval_db_path != paths.auth_db_path:
        ensure_schema(str(paths.operation_approval_db_path))
    if paths.training_db_path not in {paths.auth_db_path, paths.operation_approval_db_path}:
        ensure_schema(str(paths.training_db_path))


class DependencyFactory:
    def __init__(self, config: DependencyBuildConfig):
        self._config = config
        self._paths = resolve_dependency_db_paths(config)

    @staticmethod
    def _notification_retry_seconds() -> int:
        return int(settings.NOTIFICATION_RETRY_INTERVAL_SECONDS or 60)

    @classmethod
    def _build_notification_manager(
        cls,
        *,
        db_path: str,
        audit_log_manager: AuditLogManager,
    ) -> NotificationManager:
        manager = NotificationManager(
            store=NotificationStore(db_path=db_path),
            audit_log_manager=audit_log_manager,
            retry_interval_seconds=cls._notification_retry_seconds(),
        )
        _ensure_default_notification_channels(manager)
        return manager

    def build(self) -> AppDependencies:
        ensure_dependency_schemas(self._paths)
        runtime = self._build_shared_runtime()
        deps = self._package_app_dependencies(runtime)
        self._attach_operation_approval_service(deps=deps, runtime=runtime)
        deps.knowledge_ingestion_manager = KnowledgeIngestionManager(deps=deps)
        return deps

    def _build_shared_runtime(self) -> _SharedRuntime:
        auth_db_path = str(self._paths.auth_db_path)
        training_db_path = str(self._paths.training_db_path)
        inbox_db_path = str(self._paths.inbox_db_path)

        chat_session_store = ChatSessionStore(db_path=auth_db_path)
        chat_ownership_store = ChatOwnershipStore(db_path=auth_db_path)
        auth_session_store = AuthSessionStore(db_path=auth_db_path)
        auth_session_manager = AuthSessionManager(port=auth_session_store)

        ragflow_conn = create_ragflow_connection()
        ragflow_service = RagflowService(connection=ragflow_conn)
        ragflow_chat_service = RagflowChatService(
            session_store=chat_session_store,
            connection=ragflow_conn,
        )

        knowledge_directory_store = KnowledgeDirectoryStore(db_path=auth_db_path)
        knowledge_tree_manager = KnowledgeTreeManager(store=knowledge_directory_store)
        knowledge_management_manager = KnowledgeManagementManager(
            tree_manager=knowledge_tree_manager,
            directory_store=knowledge_directory_store,
            ragflow_service=ragflow_service,
        )
        chat_management_manager = ChatManagementManager(
            store=chat_ownership_store,
            ragflow_chat_service=ragflow_chat_service,
            knowledge_management_manager=knowledge_management_manager,
        )

        permission_group_folder_store = PermissionGroupFolderStore(db_path=auth_db_path)
        permission_group_folder_manager = PermissionGroupFolderManager(store=permission_group_folder_store)

        electronic_signature_store = ElectronicSignatureStore(db_path=auth_db_path)
        electronic_signature_service = ElectronicSignatureService(store=electronic_signature_store)

        audit_log_store = AuditLogStore(db_path=auth_db_path)
        audit_log_manager = AuditLogManager(store=audit_log_store)
        notification_manager = self._build_notification_manager(
            db_path=auth_db_path,
            audit_log_manager=audit_log_manager,
        )

        user_inbox_store = UserInboxStore(db_path=inbox_db_path)
        user_inbox_service = UserInboxService(store=user_inbox_store)

        org_directory_store = OrgDirectoryStore(db_path=auth_db_path)

        return _SharedRuntime(
            chat_session_store=chat_session_store,
            chat_ownership_store=chat_ownership_store,
            auth_session_store=auth_session_store,
            auth_session_manager=auth_session_manager,
            ragflow_service=ragflow_service,
            ragflow_chat_service=ragflow_chat_service,
            data_security_store=DataSecurityStore(db_path=auth_db_path),
            chat_message_sources_store=ChatMessageSourcesStore(db_path=auth_db_path),
            search_config_store=SearchConfigStore(db_path=auth_db_path),
            knowledge_directory_store=knowledge_directory_store,
            knowledge_tree_manager=knowledge_tree_manager,
            knowledge_management_manager=knowledge_management_manager,
            chat_management_manager=chat_management_manager,
            permission_group_folder_store=permission_group_folder_store,
            permission_group_folder_manager=permission_group_folder_manager,
            electronic_signature_store=electronic_signature_store,
            electronic_signature_service=electronic_signature_service,
            emergency_change_service=EmergencyChangeService(db_path=auth_db_path),
            supplier_qualification_service=SupplierQualificationService(db_path=auth_db_path),
            training_compliance_service=TrainingComplianceService(db_path=training_db_path),
            watermark_policy_store=WatermarkPolicyStore(db_path=auth_db_path),
            user_store=UserStore(db_path=auth_db_path),
            kb_store=KbStore(db_path=auth_db_path),
            deletion_log_store=DeletionLogStore(db_path=auth_db_path),
            download_log_store=DownloadLogStore(db_path=auth_db_path),
            audit_log_store=audit_log_store,
            audit_log_manager=audit_log_manager,
            org_directory_store=org_directory_store,
            org_structure_manager=OrgStructureManager(store=org_directory_store),
            permission_group_store=PermissionGroupStore(database_path=auth_db_path),
            user_tool_permission_store=UserToolPermissionStore(
                connection_factory=lambda: connect_sqlite(auth_db_path)
            ),
            upload_settings_store=UploadSettingsStore(db_path=auth_db_path),
            patent_download_store=PatentDownloadStore(db_path=auth_db_path),
            paper_download_store=PaperDownloadStore(db_path=auth_db_path),
            package_drawing_store=PackageDrawingStore(db_path=auth_db_path),
            notification_manager=notification_manager,
            user_inbox_store=user_inbox_store,
            user_inbox_service=user_inbox_service,
        )

    @staticmethod
    def _package_app_dependencies(runtime: _SharedRuntime) -> AppDependencies:
        return AppDependencies(
            user_store=runtime.user_store,
            kb_store=runtime.kb_store,
            ragflow_service=runtime.ragflow_service,
            deletion_log_store=runtime.deletion_log_store,
            download_log_store=runtime.download_log_store,
            audit_log_store=runtime.audit_log_store,
            audit_log_manager=runtime.audit_log_manager,
            ragflow_chat_service=runtime.ragflow_chat_service,
            chat_session_store=runtime.chat_session_store,
            auth_session_store=runtime.auth_session_store,
            auth_session_manager=runtime.auth_session_manager,
            chat_message_sources_store=runtime.chat_message_sources_store,
            permission_group_store=runtime.permission_group_store,
            user_tool_permission_store=runtime.user_tool_permission_store,
            org_directory_store=runtime.org_directory_store,
            org_structure_manager=runtime.org_structure_manager,
            data_security_store=runtime.data_security_store,
            search_config_store=runtime.search_config_store,
            upload_settings_store=runtime.upload_settings_store,
            patent_download_store=runtime.patent_download_store,
            paper_download_store=runtime.paper_download_store,
            package_drawing_store=runtime.package_drawing_store,
            knowledge_directory_store=runtime.knowledge_directory_store,
            knowledge_directory_manager=runtime.knowledge_tree_manager,
            knowledge_tree_manager=runtime.knowledge_tree_manager,
            knowledge_management_manager=runtime.knowledge_management_manager,
            knowledge_ingestion_manager=None,
            permission_group_folder_store=runtime.permission_group_folder_store,
            permission_group_folder_manager=runtime.permission_group_folder_manager,
            chat_management_manager=runtime.chat_management_manager,
            electronic_signature_store=runtime.electronic_signature_store,
            electronic_signature_service=runtime.electronic_signature_service,
            emergency_change_service=runtime.emergency_change_service,
            supplier_qualification_service=runtime.supplier_qualification_service,
            training_compliance_service=runtime.training_compliance_service,
            notification_manager=runtime.notification_manager,
            notification_service=runtime.notification_manager,
            user_inbox_store=runtime.user_inbox_store,
            user_inbox_service=runtime.user_inbox_service,
            operation_approval_service=None,
            watermark_policy_store=runtime.watermark_policy_store,
        )

    def _build_operation_approval_dependencies(
        self,
        runtime: _SharedRuntime,
    ) -> _OperationApprovalDependencySet:
        if self._paths.operation_approval_db_path == self._paths.auth_db_path:
            return _OperationApprovalDependencySet(
                user_store=runtime.user_store,
                notification_service=runtime.notification_manager,
                external_notification_service=runtime.notification_manager,
                inbox_service=runtime.user_inbox_service,
                electronic_signature_service=runtime.electronic_signature_service,
            )

        control_db_path = str(self._paths.operation_approval_db_path)
        external_audit_log_manager = AuditLogManager(store=AuditLogStore(db_path=control_db_path))
        external_notification_service = self._build_notification_manager(
            db_path=control_db_path,
            audit_log_manager=external_audit_log_manager,
        )
        return _OperationApprovalDependencySet(
            user_store=UserStore(db_path=control_db_path),
            notification_service=runtime.notification_manager,
            external_notification_service=external_notification_service,
            inbox_service=UserInboxService(store=UserInboxStore(db_path=control_db_path)),
            # Operation approvals consume signature tokens issued by shared auth routes.
            electronic_signature_service=runtime.electronic_signature_service,
        )

    def _attach_operation_approval_service(
        self,
        *,
        deps: AppDependencies,
        runtime: _SharedRuntime,
    ) -> None:
        operation_approval_dependencies = self._build_operation_approval_dependencies(runtime)
        deps.operation_approval_service = OperationApprovalService(
            store=OperationApprovalStore(db_path=str(self._paths.operation_approval_db_path)),
            user_store=operation_approval_dependencies.user_store,
            inbox_service=operation_approval_dependencies.inbox_service,
            notification_service=operation_approval_dependencies.notification_service,
            external_notification_service=operation_approval_dependencies.external_notification_service,
            electronic_signature_service=operation_approval_dependencies.electronic_signature_service,
            deps=deps,
            execution_deps_resolver=self._config.operation_approval_execution_deps_resolver,
        )
        deps.operation_approval_service.migrate_legacy_document_reviews()


def create_app_dependencies(
    *,
    db_path: str | None = None,
    operation_approval_control_db_path: str | None = None,
    training_compliance_db_path: str | None = None,
    operation_approval_execution_deps_resolver: Callable[[int | str], AppDependencies] | None = None,
) -> AppDependencies:
    return DependencyFactory(
        DependencyBuildConfig(
            db_path=db_path,
            operation_approval_control_db_path=operation_approval_control_db_path,
            training_compliance_db_path=training_compliance_db_path,
            operation_approval_execution_deps_resolver=operation_approval_execution_deps_resolver,
        )
    ).build()
