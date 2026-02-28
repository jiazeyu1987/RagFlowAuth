from dataclasses import dataclass

from backend.database.paths import resolve_auth_db_path
from backend.database.schema_migrations import ensure_schema
from backend.services.chat_session_store import ChatSessionStore
from backend.services.data_security import DataSecurityStore
from backend.services.audit_log_store import AuditLogStore
from backend.services.chat_message_sources_store import ChatMessageSourcesStore
from backend.services.deletion_log_store import DeletionLogStore
from backend.services.download_log_store import DownloadLogStore
from backend.services.kb_store import KbStore
from backend.services.permission_group_store import PermissionGroupStore
from backend.services.patent_download.store import PatentDownloadStore
from backend.services.paper_download.store import PaperDownloadStore
from backend.services.ragflow_connection import create_ragflow_connection
from backend.services.ragflow_chat_service import RagflowChatService
from backend.services.ragflow_service import RagflowService
from backend.services.org_directory_store import OrgDirectoryStore
from backend.services.user_store import UserStore
from backend.services.search_config_store import SearchConfigStore


@dataclass
class AppDependencies:
    user_store: UserStore
    kb_store: KbStore
    ragflow_service: RagflowService
    deletion_log_store: DeletionLogStore
    download_log_store: DownloadLogStore
    audit_log_store: AuditLogStore
    ragflow_chat_service: RagflowChatService
    chat_session_store: ChatSessionStore
    chat_message_sources_store: ChatMessageSourcesStore
    permission_group_store: PermissionGroupStore
    org_directory_store: OrgDirectoryStore
    data_security_store: DataSecurityStore
    search_config_store: SearchConfigStore
    patent_download_store: PatentDownloadStore
    paper_download_store: PaperDownloadStore


def create_dependencies(db_path: str | None = None) -> AppDependencies:
    db_path = resolve_auth_db_path(db_path)

    ensure_schema(str(db_path))

    chat_session_store = ChatSessionStore(db_path=str(db_path))
    ragflow_conn = create_ragflow_connection()
    data_security_store = DataSecurityStore(db_path=str(db_path))
    chat_message_sources_store = ChatMessageSourcesStore(db_path=str(db_path))
    search_config_store = SearchConfigStore(db_path=str(db_path))

    return AppDependencies(
        user_store=UserStore(db_path=str(db_path)),
        kb_store=KbStore(db_path=str(db_path)),
        ragflow_service=RagflowService(connection=ragflow_conn),
        deletion_log_store=DeletionLogStore(db_path=str(db_path)),
        download_log_store=DownloadLogStore(db_path=str(db_path)),
        audit_log_store=AuditLogStore(db_path=str(db_path)),
        ragflow_chat_service=RagflowChatService(session_store=chat_session_store, connection=ragflow_conn),
        chat_session_store=chat_session_store,
        chat_message_sources_store=chat_message_sources_store,
        permission_group_store=PermissionGroupStore(database_path=str(db_path)),
        org_directory_store=OrgDirectoryStore(db_path=str(db_path)),
        data_security_store=data_security_store,
        search_config_store=search_config_store,
        patent_download_store=PatentDownloadStore(db_path=str(db_path)),
        paper_download_store=PaperDownloadStore(db_path=str(db_path)),
    )
