# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Production Server

- **IP Address**: `172.30.30.57`
- **Username**: `root`
- **Description**: Remote Linux server where RagflowAuth is deployed via Docker

When user mentions "服务器" or "远程服务器", they refer to this server.

## Layout

```
RagflowAuth/
├── backend/     # FastAPI backend (port: 8001)
│   ├── app/         # Routers, DI, auth, permission resolver
│   ├── services/    # Stores + RAGFlow clients
│   ├── database/    # SQLite schema + helpers
│   ├── migrations/  # Small migration wrappers (kept for compatibility)
│   ├── scripts/     # One-off maintenance scripts
│   └── runtime/     # Unified runner (`python -m backend`)
└── fronted/     # React frontend (port: 3001)
```

## Key Commands

### Backend

Install deps:

`pip install -r backend/requirements.txt`

Initialize DB (creates default admin `admin/admin123` if missing):

`python -m backend init-db`

If upgrading from an old layout that stored data under `backend/data/`, migrate once:

`python -m backend migrate-data-dir`

Run server:

`python -m backend`

Show resolved paths (DB/uploads/RAGFlow config):

`python -m backend paths`

Backup auth DB (our data only):

- Create config: `python -m backend init-backup`
- Run backup: `python -m backend backup`

### Frontend

`cd fronted`

`npm install`

`npm start`

`npm run build`

`npm test`  # React Scripts test runner

## Data/Config Conventions

- SQLite DB default: `data/auth.db` (repo root).
- Upload dir default: `data/uploads` (repo root).
- RAGFlow config: `ragflow_config.json` (repo root).
- Backup config: `backup_config.json` (repo root).

### Deployment and Backup Tools

The `tool/` directory contains deployment automation and backup/restore utilities:

- **Remote deployment**: `deploy.ps1` for building and deploying to remote Linux servers
- **Backup download**: `tool/scripts/Download-Backup.bat` for downloading server backups
- **Restore automation**: `tool/scripts/Restore-RagflowBackup.ps1` for automated disaster recovery

See `tool/CLAUDE.md` for detailed deployment and backup documentation.

## Architecture

### Backend (FastAPI)

**Service Layer Pattern:**
- All business logic lives in `backend/services/` (stores, RAGFlow clients)
- Routers in `backend/app/modules/` are thin - they delegate to services
- Dependency injection via `AppDependencies` dataclass manages all services
- Lifecycle handled by async context manager for proper startup/shutdown

**Core Modules:**
- `auth` - Login/logout, JWT token management (AuthX)
- `users` - User CRUD operations
- `knowledge` - KB document management (upload, review, download, delete)
- `review` - Document review workflow
- `chat` - Chat/agent session management
- `ragflow` - RAGFlow integration endpoints
- `permission_groups` - Permission group CRUD
- `data_security` - Backup job management and execution

**Key Services:**
- `UserStore` - User data persistence
- `PermissionResolver` - Resolves user permissions from groups
- `RagflowService` - Main RAGFlow API integration (ragflow-sdk)
- `RagflowChatService` - Chat/agent session management
- `DataSecurityService` - Backup job scheduling and execution

### Frontend (React)

- React 18 with `react-router-dom` 6.20.0 for routing
- No Redux/Context API - lightweight state using React hooks
- Centralized API client in `src/features/*/api.js`
- Page components in `src/pages/`, features in `src/features/`

## Authorization Model

**Permission Resolver Pattern:**
- Business permissions are resolved from **permission groups (resolver)**.
- JWT `scopes` are kept for compatibility only and must not drive business authorization.
- Admin users (`role=admin`) bypass all permission checks.
- Non-admin users inherit permissions from assigned permission groups.

**Permission Scopes:**
- Knowledge bases: `ALL`, `SET` (specific KBs), or `NONE`
- Chat sessions: Similar scoping for chat/agent access
- Capabilities: Upload, Review, Download, Delete

**Permission Resolution Flow:**
1. User logs in → JWT contains user ID
2. `GET /api/auth/me` resolves permissions from assigned groups
3. Response includes `accessible_kbs`, `accessible_chats`, `can_*` flags
4. All business logic uses these resolved permissions

**Default Deny:**
- Users with no group or non-existent group get `NONE` for KB/Chat access
- `accessible_kbs` and `accessible_chats` return empty arrays

Historical "individual user permissions" tables (`user_kb_permissions`, `user_chat_permissions`) are deprecated and not used in authorization.

## Database Schema

**Key Tables:**
- `users` - User accounts (auth data, legacy `group_id` field)
- `permission_groups` - Group definitions with KB/chat scopes and capabilities
- `user_permission_groups` - Many-to-many relationship between users and groups
- `kb_documents` - Document metadata with review status and RAGFlow integration
- `chat_sessions` - Persistent chat/agent session data
- `audit_logs` - Download and deletion tracking for compliance
- `data_security_jobs` - Backup job tracking

## RAGFlow Integration

**Dual Service Model:**
- `RagflowService` - Main RAGFlow API operations using `ragflow-sdk`
- `RagflowChatService` - Separate service for chat/agent sessions

**Configuration:**
- Read from `ragflow_config.json` in repo root
- Contains `api_key` and `base_url` (e.g., `http://127.0.0.1:9380`)

**Dataset Caching:**
- Local cache of KB datasets for efficient permission resolution
- Refreshed periodically to sync with RAGFlow

## Data Security / Backup

**Backup System:**
- Two modes: Incremental (auth.db only) and Full (includes Docker volumes)
- Flexible targets: Local directories or network shares (UNC paths)
- Optional Docker service pause during backups
- Async job queueing with progress monitoring
- UI tool available: `python backup_ui.py` (saves config to `backup_ui_config.json`)

**Backup Commands:**
- `python -m backend init-backup` - Create `backup_config.json`
- `python -m backend backup` - Run backup immediately
- `backup_now.bat` - Windows batch file for manual backup

## Diagnostics

**Permission Debug Logging:**
- Enable with environment variable: `PERMDBG_ENABLED=true`
- Logs prefixed with `[PERMDBG]` for easy filtering
- Shows permission resolution steps and decisions

**Common Issues:**
- "暂无知识库可用" (No KBs available): Check user's permission group assignment and RAGFlow connectivity
- Permission denied: Verify group configuration in `permission_groups` table
- RAGFlow connection failure: Check `ragflow_config.json` `base_url` and network connectivity

## Development Notes

**Adding New Endpoints:**
1. Create router in `backend/app/modules/`
2. Add route handler that delegates to service layer
3. Inject dependencies via FastAPI's `Depends()`
4. Register router in `backend/app/main.py`

**Adding New Frontend Features:**
1. Create feature directory in `fronted/src/features/`
2. Add API client in `api.js`
3. Create page component in `fronted/src/pages/`
4. Add route in `fronted/src/App.js`

**Database Migrations:**
- Schema changes require updating `backend/database/schema_migrations.py`
- Use `backend/database/migrations.py` for compatibility wrappers
- Always test with `python -m backend init-db` on fresh database
