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

Run with hot reload (development):

`python -m backend run --reload`

Show resolved paths (DB/uploads/RAGFlow config):

`python -m backend paths`

Run backend tests (Python unittest):

```bash
cd backend
python -m unittest discover tests
```

**Backend Testing Pattern:**
- Uses Python `unittest` framework
- Tests in `backend/tests/test_*.py`
- Fake dependencies pattern: create lightweight fakes for services
- FastAPI `TestClient` for endpoint testing
- No external dependencies required (runs without RAGFlow)

Backup auth DB (our data only):

- Create config: `python -m backend init-backup`
- Run backup: `python -m backend backup`

### Frontend

`cd fronted`

`npm install`

`npm start`

`npm run build`

`npm test`  # React Scripts test runner

**E2E Testing (Playwright):**
```bash
# Regression tests (skip @integration)
npm run e2e

# Smoke tests only
npm run e2e:smoke

# Integration tests (real backend, serial)
npm run e2e:integration

# Run single spec
npx playwright test <name>.spec.js

# View test report
npm run e2e:report

# Interactive UI mode
npm run e2e:ui
```

**Test Environment Setup:**
- Backend must be running on `http://localhost:8001` (or set `E2E_FRONTEND_BASE_URL`)
- Frontend must be running on `http://localhost:8080` (default)
- Tests use fixtures from `fronted/e2e/global-setup.ts`

## Data/Config Conventions

- SQLite DB default: `data/auth.db` (repo root).
- Upload dir default: `data/uploads` (repo root).
- RAGFlow config: `ragflow_config.json` (repo root).
- Backup config: `backup_config.json` (repo root).
- Data Security (backup replica): `data_security_jobs` table in DB, configured via UI.

**Backend Runtime Commands:**
The unified `python -m backend` CLI provides multiple commands:
- `python -m backend` - Start server (default)
- `python -m backend run --reload` - Start with hot reload
- `python -m backend init-db` - Initialize database with default admin
- `python -m backend ensure-schema` - Ensure schema without admin creation
- `python -m backend paths` - Show resolved paths
- `python -m backend migrate-data-dir` - Migrate legacy data locations
- `python -m backend init-backup` - Create backup config
- `python -m backend backup` - Run backup immediately

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
- `org_directory` - Organizational directory (sync users from RAGFlow)

**Key Services:**
- `UserStore` - User data persistence
- `PermissionResolver` - Resolves user permissions from groups
- `RagflowService` - Main RAGFlow API integration (ragflow-sdk)
- `RagflowChatService` - Chat/agent session management
- `DataSecurityService` - Backup job scheduling and execution
- `BackupReplicaService` - Automatic backup replication to network shares

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
- `org_directory` - Organizational directory (users sync from RAGFlow)
- `kb_documents` - Document metadata with review status and RAGFlow integration
- `chat_sessions` - Persistent chat/agent session data
- `audit_logs` - Download and deletion tracking for compliance
- `data_security_jobs` - Backup job tracking
- `data_security_settings` - Backup and replica configuration

**Schema Organization:**
- Database schema is modular: `backend/database/schema/*.py`
- Each module has a `ensure_table()` and optional migration function
- `backend/database/schema/ensure.py` orchestrates all schema updates
- Migrations run automatically on startup via `ensure_schema()`

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
- Scheduled backups via UI (Data Security page)
- Automatic replica to network shares (SMB/CIFS)
- UI tool available: `python backup_ui.py` (saves config to `backup_ui_config.json`)

**Backup Replica (New):**
- Automatic replication after backup completes
- Requires SMB share mounted on host at `/mnt/replica`
- Docker bind mount: `/mnt/replica:/replica` in backend container
- Two subdirectory formats: `flat` (all backups in one dir) or `date` (YYYY/MM/DD)
- Atomic copy: temp directory → DONE marker → rename
- Configured via UI: Data Security → "自动复制设置"

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
- Backup replica fails: Check SMB mount on host (`/mnt/replica`) and Docker bind mount (`/replica`)
- Tests fail: Ensure backend and frontend are running, check `E2E_FRONTEND_BASE_URL`

**Recent Feature Additions:**
- **Scheduled Backups**: Data Security page allows configuring scheduled backup jobs
- **Backup Replica**: Automatic replication to Windows network shares after backup completes
- **Organizational Directory**: User sync from RAGFlow with group assignment support
- **E2E Test Suite**: Comprehensive Playwright tests with smoke/integration/regression tags

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

**E2E Testing:**
- Tests in `fronted/e2e/tests/*.spec.js` using Playwright
- Tag tests with `@smoke`, `@integration`, or no tag (regression)
- Use `data-testid` attributes for test selectors
- Fixtures and global setup in `fronted/e2e/global-setup.ts`

**Database Migrations:**
- Schema changes go in `backend/database/schema/<module>.py`
- Each schema module has `ensure_table()` and optional migration functions
- `backend/database/schema/ensure.py` orchestrates all migrations
- Migrations run automatically on startup via `ensure_schema()`
- Always test with `python -m backend init-db` on fresh database

**Deployment - How to Deploy Local Changes to Server:**

After modifying code on Windows (local), deploy to remote server using this workflow:

1. **Build Docker images locally:**
   ```powershell
   cd D:\ProjectPackage\RagflowAuth\docker
   docker compose build
   ```
   This creates images tagged as `ragflowauth-backend:local` and `ragflowauth-frontend:local`

2. **Tag images with production tag:**
   ```powershell
   docker tag ragflowauth-backend:local ragflowauth-backend:2025-01-25-scheduler-fix-v2
   docker tag ragflowauth-frontend:local ragflowauth-frontend:2025-01-25-scheduler-fix-v2
   ```
   Use the same tag that's currently running on the server

3. **Export images to tar file:**
   ```powershell
   docker save -o "D:\ProjectPackage\RagflowAuth\dist\ragflowauth-images.tar" ragflowauth-backend:2025-01-25-scheduler-fix-v2 ragflowauth-frontend:2025-01-25-scheduler-fix-v2
   ```

4. **Transfer tar to server:**
   ```bash
   scp "D:\ProjectPackage\RagflowAuth\dist\ragflowauth-images.tar" root@172.30.30.57:/tmp/
   ```

5. **Load images and restart container on server:**
   ```bash
   ssh root@172.30.30.57
   docker load -i /tmp/ragflowauth-images.tar
   docker stop ragflowauth-backend
   docker rm ragflowauth-backend
   docker run -d --name ragflowauth-backend --network ragflowauth-network -p 8001:8001 \
     -v /opt/ragflowauth/data:/app/data \
     -v /opt/ragflowauth/uploads:/app/uploads \
     -v /opt/ragflowauth/ragflow_config.json:/app/ragflow_config.json:ro \
     -v /opt/ragflowauth/backup_config.json:/app/backup_config.json:ro \
     -v /opt/ragflowauth/ragflow_compose:/app/ragflow_compose:ro \
     -v /mnt/replica:/mnt/replica \
     -v /var/run/docker.sock:/var/run/docker.sock \
     ragflowauth-backend:2025-01-25-scheduler-fix-v2
   rm -f /tmp/ragflowauth-images.tar
   ```

6. **Verify deployment:**
   ```bash
   docker ps | grep ragflowauth-backend
   docker logs -f ragflowauth-backend
   ```

**Alternative: Use deploy.ps1 script (automated):**
```powershell
cd D:\ProjectPackage\RagflowAuth
.\tool\scripts\deploy.ps1 -Tag "2025-01-25-scheduler-fix-v2" -ComposeFile "docker\docker-compose.yml"
```

**Important Notes:**
- Code changes in Windows local files don't automatically sync to server
- Server runs code from Docker image, not from mounted volume
- Must rebuild image and redeploy container to apply code changes
- Keep track of the current tag used in production (check with `ssh root@172.30.30.57 "docker images | grep ragflowauth-backend"`)

**Docker Image Cleanup:**
- **Default policy**: Only keep current running version, delete all other versions
- Auto-cleanup: Deployment script removes all old images automatically
- **Safety**: Never deletes images used by running containers
- Manual cleanup: Upload and run `tool/scripts/cleanup-images.sh` on server
- Preview mode (safe): `/tmp/cleanup-images.sh --dry-run`
- Custom retention: `/tmp/cleanup-images.sh --keep 3` (keep last 3 versions for rollback)
- View image usage: `ssh root@172.30.30.57 "docker system df"`

**Note**: The default cleanup policy (`--keep 1`) removes rollback capability. If you need to keep previous versions for rollback, use `--keep 2` or higher.

**Quick Restart (No Rebuild):**
If you've already transferred images to the server and just need to restart containers:
```bash
# On server
ssh root@172.30.30.57
/opt/ragflowauth/quick-restart.sh --tag 2025-01-25-scheduler-fix-v2
```

This is faster than full deployment when only configuration changes, not code.
