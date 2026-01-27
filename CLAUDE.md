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

**⚠️ CRITICAL WARNING: 版本同步问题**

**问题**: 修改了代码但服务器运行的是旧版本
**原因**: Docker 使用了缓存的旧镜像，或者跳过了镜像构建步骤

**解决方案**:
1. ❌ **永远不要**在代码修改后使用 `-SkipBuild` 参数
2. ✅ **每次代码修改**都必须完整执行构建流程
3. ✅ 部署前验证镜像包含最新代码

---

### 步骤 1: 验证代码修改

在开始部署前，确认你修改了哪些文件：

```bash
# 例如：检查最近修改的文件
git status
git diff backend/services/data_security/replica_service.py
```

---

### 步骤 2: 强制重新构建 Docker 镜像（禁止使用缓存）

**⚠️ 重要**: 不要使用 `--no-cache` 除非必要（会非常慢）。标准构建会自动处理依赖变化。

```powershell
# 1. 删除旧的 local 镜像，强制重新构建
docker rmi ragflowauth-backend:local ragflowauth-frontend:local 2>$null

# 2. 重新构建（不使用缓存层）
cd D:\ProjectPackage\RagflowAuth\docker
docker compose build --no-cache
```

**或者使用标准构建（推荐，更快）**:
```powershell
cd D:\ProjectPackage\RagflowAuth\docker
docker compose build
```

---

### 步骤 3: 验证镜像包含最新代码

**⚠️ 关键步骤**: 部署前必须验证！

```bash
# 检查镜像内的代码（以 replica_service.py 为例）
docker run --rm ragflowauth-backend:local grep -A 5 "Check if volumes directory" /app/backend/services/data_security/replica_service.py

# 应该看到：
# # Check if volumes directory in container is actually empty
#     container_has_volumes_files = False
#     if volumes_container.exists():
```

**如果看不到新代码**: 说明 Docker 使用了缓存，返回步骤 2 使用 `--no-cache`

---

### 步骤 4: 部署到服务器

```powershell
cd D:\ProjectPackage\RagflowAuth
.\tool\scripts\deploy.ps1 -Tag "你的版本标签"
```

**⚠️ 禁止使用**: `-SkipBuild` 参数（仅在完全确认没有代码修改时使用）

---

### 步骤 5: 验证部署成功

```bash
# 1. 检查容器运行的镜像版本
ssh root@172.30.30.57 "docker ps | grep ragflowauth-backend"

# 2. 检查服务器上的镜像时间戳
ssh root@172.30.30.57 "docker images | grep ragflowauth-backend"

# 3. 验证代码版本（可选）
ssh root@172.30.30.57 "docker exec ragflowauth-backend grep -A 5 'Check if volumes directory' /app/backend/services/data_security/replica_service.py"
```

---

## 快速检查清单

部署前必须确认：

- [ ] 修改了哪些 Python/JS 代码文件？
- [ ] 是否重新运行了 `docker compose build`？
- [ ] 是否删除了旧的 `:local` 镜像？
- [ ] 是否验证了镜像包含最新代码？
- [ ] 是否使用了版本标签（而不是 `:local`）？

---

## 常见错误和解决方案

### 错误 1: 代码修改后服务器还是旧版本

**原因**: 使用了缓存的旧镜像，或跳过了构建步骤

**解决**:
```powershell
# 强制重新构建
docker rmi ragflowauth-backend:local ragflowauth-frontend:local
cd docker
docker compose build --no-cache
```

### 错误 2: 部署后功能不正常

**原因**: 可能使用了错误的镜像标签

**解决**:
```bash
# 检查当前运行的镜像
ssh root@172.30.30.57 "docker ps --format '{{.Image}}' | grep ragflowauth"

# 应该看到: ragflowauth-backend:你的版本标签
# 如果看到 ragflowauth-backend:local，说明使用了错误的标签
```

### 错�误 3: Docker 构建很快但代码没更新

**原因**: Docker 使用了缓存层

**解决**:
```powershell
# 删除镜像并重新构建
docker rmi ragflowauth-backend:local
docker compose build --no-cache backend
```

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

---

## Version Numbering Standard

**Format**: `major.minor.patch-description`

### Version Format Rules

- **major**: Major version (breaking changes, major features)
- **minor**: Minor version (new features, backward compatible)
- **patch**: Patch version (bug fixes, small improvements)
- **description**: Optional hyphen-separated description of changes

### Examples

Good version numbers:
- ✅ `1.0.0` - Initial stable release
- ✅ `1.0.1-replica-fix` - Bug fix for Windows sync
- ✅ `1.1.0-scheduler-support` - New scheduled backup feature
- ✅ `2.0.0-auth-redesign` - Major auth system redesign

Bad version numbers (DO NOT USE):
- ❌ `v1` - Vague, no semantic info
- ❌ `2025-01-25-scheduler-fix-v2` - Date-based, redundant
- ❌ `fix-complete` - No version number
- ❌ `latest` - Meaningless for tracking

### When to Increment Versions

**Patch (third digit)**: Bug fixes, small improvements
- Example: `1.0.0` → `1.0.1`
- Fix Windows sync bug
- Improve error messages
- Update dependencies

**Minor (second digit)**: New features, backward compatible
- Example: `1.0.1` → `1.1.0`
- Add scheduled backup feature
- Add organizational directory sync
- Add new API endpoints

**Major (first digit)**: Breaking changes, major redesigns
- Example: `1.1.0` → `2.0.0`
- Redesign authentication system
- Database schema changes requiring migration
- Remove deprecated features

### Current Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-01-27 | Initial stable release with data security and replica features |
| 1.0.1 | 2025-01-27 | Fixed Windows sync bug (volumes files not copying) |
| 1.0.2 | 2025-01-27 | Fixed replica service path conversion for /app/data/backups |
| 1.0.3 | 2025-01-27 | Dynamic image detection instead of hardcoded name in docker_tar_volume |
| 1.0.4 | 2025-01-27 | Fixed Docker images backup path conversion (read-only filesystem error) |
| 1.0.5 | 2025-01-27 | Fixed volume backup path conversion (volumes written to wrong location) |
| 1.1.0 | 2025-01-27 | Added scheduled backup support with cron expressions |

### Migration from Old Naming Scheme

If you have old images with non-standard names, retag them before deploying:

```bash
# Old: ragflowauth-backend:2025-01-25-scheduler-fix-v2
# New: ragflowauth-backend:1.1.0-scheduler-support

docker tag ragflowauth-backend:2025-01-25-scheduler-fix-v2 ragflowauth-backend:1.1.0-scheduler-support
docker tag ragflowauth-frontend:2025-01-25-scheduler-fix-v2 ragflowauth-frontend:1.1.0-scheduler-support
```

### Best Practices

1. **Always use semantic versioning**: `major.minor.patch-description`
2. **Keep descriptions short**: Max 2-3 words, kebab-case
3. **Update CLAUDE.md**: Add new version to history table after each release
4. **Use meaningful tags**: Describe the feature or fix, not the date
5. **Document breaking changes**: In major version releases

---

## Backup System Best Practices

### Critical Path Conversion Rules

**The #1 Rule**: Always handle `/app/data/backups` **before** generic `/app/data/` paths.

```python
# CORRECT order (specific first, then general)
if path_str.startswith("/app/data/backups"):
    path_str = path_str.replace("/app/data/backups", "/opt/ragflowauth/backups", 1)
elif path_str.startswith("/app/data/"):
    path_str = path_str.replace("/app/data", "/opt/ragflowauth/data", 1)
```

**Why this matters**:
- `/app/data/backups` → `/opt/ragflowauth/backups` (read-write ✅)
- `/app/data` → `/opt/ragflowauth/data` (read-only ❌)

If you check `/app/data/` first, `/app/data/backups` will be incorrectly converted to `/opt/ragflowauth/data/backups`, causing:
- Read-only filesystem errors
- Files written to wrong location
- Silent failures (backup succeeds but files are inaccessible)

### Docker Mount Architecture

```
Host Path                    Container Path         Mode
/opt/ragflowauth/data      → /app/data            RW (main data)
/opt/ragflowauth/uploads   → /app/uploads         RW (uploads)
/opt/ragflowauth/backups   → /app/data/backups    RW (backups - SPECIAL!)
/opt/ragflowauth/data      → /opt/ragflowauth/data RO (read-only view)
/mnt/replica               → /mnt/replica         RW (Windows share)
```

**Key insight**: `/app/data/backups` has its own dedicated mount, separate from `/app/data`.

### Functions That Need Path Conversion

Any function that writes files from within the container must convert paths:

1. **docker_save_images()** - Saves Docker images to tar
2. **docker_tar_volume()** - Backs up Docker volumes
3. **replica_service._copy_directory()** - Copies backups to Windows share
4. **replica_service._convert_to_host_path()** - General path converter

**Pattern**:
```python
def write_file_from_container(container_path: Path) -> None:
    # Convert to host path
    host_path = _convert_to_host_path(container_path)

    # Execute command on host (via Docker socket)
    run_cmd(["docker", "run", "-v", f"{host_path}:/output", ...])
```

### Testing Backup System

**Before deploying**:
1. Run manual full backup from UI
2. Check local backup directory: `/opt/ragflowauth/backups/migration_pack_*/`
3. Verify contents:
   - `auth.db` (320KB+)
   - `images.tar` (8-9GB for full backup)
   - `volumes/*.tar.gz` (30MB+ for RAGFlow volumes)
4. Check Windows share: `//192.168.112.72/backup/RagflowAuth/`
5. Verify all files exist on Windows share
6. Check for DONE marker and replication_manifest.json

**After deploy**:
1. Wait for scheduled backup to run automatically
2. Verify job completed: `SELECT status FROM backup_jobs ORDER BY id DESC LIMIT 1`
3. Check backup size matches expectations
4. Verify Windows sync completed

### Common Pitfalls

❌ **Hardcoding image names**:
```python
# WRONG - breaks when image updates
image = "ragflowauth-backend:2025-01-25-scheduler-fix-v2"

# CORRECT - dynamic detection
code, out = run_cmd(["docker", "ps", "--filter", "name=ragflowauth-backend", "--format", "{{.Image}}"])
image = out.strip() if code == 0 and out else "ragflowauth-backend:latest"
```

❌ **Forgetting to check specific paths first**:
```python
# WRONG - /app/data/backups gets converted incorrectly
if path.startswith("/app/data/"):
    return path.replace("/app/data", "/opt/ragflowauth/data", 1)
elif path.startswith("/app/data/backups"):
    return path.replace("/app/data/backups", "/opt/ragflowauth/backups", 1)

# CORRECT - specific paths first
if path.startswith("/app/data/backups"):
    return path.replace("/app/data/backups", "/opt/ragflowauth/backups", 1)
elif path.startswith("/app/data/"):
    return path.replace("/app/data", "/opt/ragflowauth/data", 1)
```

❌ **Assuming files exist in container view**:
```python
# WRONG - file is on host, not in container
if dest_path.exists():
    size = dest_path.stat().st_size

# CORRECT - check both container and host paths
import os
host_path = str(dest_path).replace("/app/data/backups", "/opt/ragflowauth/backups", 1)
if os.path.exists(host_path):
    size = os.path.getsize(host_path)
```

### Backup Verification Checklist

- [ ] Local backup directory created
- [ ] auth.db present and > 300KB
- [ ] images.tar present (if full backup) and > 8GB
- [ ] volumes/ directory contains 4 .tar.gz files (ES, MySQL, Redis, MinIO)
- [ ] Total backup size > 8.8GB (full) or > 30MB (incremental)
- [ ] Windows share has matching directory
- [ ] Windows share contains DONE marker
- [ ] replication_manifest.json present
- [ ] Backup job status = "completed"
- [ ] Backup job message = "备份完成（已同步）"

### Deployment Safety

1. **Always test locally first**:
   ```bash
   cd docker
   docker compose build backend
   docker compose up
   # Test backup from UI
   ```

2. **Use semantic versioning**:
   - Patch: Bug fixes (1.0.5 → 1.0.6)
   - Minor: New features (1.0.5 → 1.1.0)
   - Major: Breaking changes (1.0.5 → 2.0.0)

3. **Keep only one running version**:
   - Deploy script automatically removes old images
   - Prevents disk space waste
   - Ensures predictable behavior

4. **Verify before cleaning up**:
   ```bash
   # Check backup exists on Windows share
   ls -lh /mnt/replica/RagflowAuth/migration_pack_*/

   # Only then delete old backups locally
   rm -rf /opt/ragflowauth/backups/migration_pack_old_*/
   ```

### Troubleshooting Backup Failures

**Symptom**: "备份完成" but no images.tar or volumes on Windows share

**Diagnosis**:
```bash
# 1. Check job details
ssh root@172.30.30.57 "docker exec ragflowauth-backend sqlite3 /app/data/auth.db 'SELECT id, status, message, detail FROM backup_jobs ORDER BY id DESC LIMIT 1'"

# 2. Check local backup
ssh root@172.30.30.57 "ls -lah /opt/ragflowauth/backups/migration_pack_*/"

# 3. Check for files in wrong location
ssh root@172.30.30.57 "find /opt/ragflowauth/data/ -name 'migration_pack_*' 2>/dev/null"
```

**Common fixes**:
- Path conversion bug → Update docker_utils.py
- Missing /mnt/replica mount → Add to docker run command
- Read-only error → Check path conversion order
- Image not found → Use dynamic detection instead of hardcoded name

---
