from dataclasses import dataclass

from backend.database.paths import resolve_auth_db_path
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
from backend.services.knowledge_ingestion import KnowledgeIngestionManager
from backend.services.knowledge_tree import KnowledgeTreeManager


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
    knowledge_ingestion_manager: KnowledgeIngestionManager | None
    permission_group_folder_store: PermissionGroupFolderStore
    permission_group_folder_manager: PermissionGroupFolderManager


def create_dependencies(db_path: str | None = None) -> AppDependencies:
    db_path = resolve_auth_db_path(db_path)

    ensure_schema(str(db_path))

    chat_session_store = ChatSessionStore(db_path=str(db_path))
    auth_session_store = AuthSessionStore(db_path=str(db_path))
    auth_session_manager = AuthSessionManager(port=auth_session_store)
    ragflow_conn = create_ragflow_connection()
    data_security_store = DataSecurityStore(db_path=str(db_path))
    chat_message_sources_store = ChatMessageSourcesStore(db_path=str(db_path))
    search_config_store = SearchConfigStore(db_path=str(db_path))
    knowledge_directory_store = KnowledgeDirectoryStore(db_path=str(db_path))
    knowledge_tree_manager = KnowledgeTreeManager(store=knowledge_directory_store)
    knowledge_directory_manager = knowledge_tree_manager
    permission_group_folder_store = PermissionGroupFolderStore(db_path=str(db_path))
    permission_group_folder_manager = PermissionGroupFolderManager(store=permission_group_folder_store)

    audit_log_store = AuditLogStore(db_path=str(db_path))
    audit_log_manager = AuditLogManager(store=audit_log_store)

    deps = AppDependencies(
        user_store=UserStore(db_path=str(db_path)),
        kb_store=KbStore(db_path=str(db_path)),
        ragflow_service=RagflowService(connection=ragflow_conn),
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
        knowledge_ingestion_manager=None,
        permission_group_folder_store=permission_group_folder_store,
        permission_group_folder_manager=permission_group_folder_manager,
    )
    deps.knowledge_ingestion_manager = KnowledgeIngestionManager(deps=deps)
    return deps
