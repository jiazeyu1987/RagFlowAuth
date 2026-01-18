# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Auth** is a standalone authentication and authorization system for managing knowledge base document uploads and reviews in the RagInt ecosystem. It provides a role-based access control (RBAC) system with JWT authentication and a document approval workflow.

**NOTE:** This codebase contains two backend implementations:
- `backend/` - Legacy Flask implementation (deprecated, uses Casbin)
- `backend/` - Current FastAPI + AuthX implementation (active)

**Always work with `backend/` unless specifically maintaining legacy code.**

## Architecture Overview

```
Auth/
├── backend/     # FastAPI backend (port: 8001) - ACTIVE
│   ├── api/         # API endpoints (auth, users, knowledge, review, ragflow, user_kb_permissions)
│   ├── services/    # Business logic stores (user, kb, ragflow, user_kb_permission, deletion_log, download_log)
│   ├── core/        # Security (AuthX JWT), scopes configuration
│   ├── models/      # Pydantic models (user, document, auth)
│   ├── database/    # Database initialization
│   ├── data/        # SQLite database + uploads
│   ├── config.py    # Configuration (pydantic-settings)
│   ├── main.py      # FastAPI app factory
│   └── dependencies.py  # Dependency injection container
│
├── backend/         # Flask backend (DEPRECATED - uses Casbin)
│
└── fronted/         # React frontend (port: 3001)
    └── src/
        ├── pages/      # Page components (login, dashboard, users, documents, audit)
        ├── components/ # Reusable components (Layout, PermissionGuard)
        ├── hooks/      # React hooks (useAuth)
        └── api/        # API client (authClient)
```

## Development Commands

### Initial Setup

**Install Backend Dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

**Install Frontend Dependencies:**
```bash
cd fronted
npm install
```

**Initialize Database:**
```bash
cd backend
python -m database.init_db
```

**Default Admin Credentials:**
- Username: `admin`
- Password: `admin123`

### Running the Application

**Start Backend (port 8001):**
```bash
cd backend
python -m main
# Or directly:
uvicorn main:app --reload --port 8001
```

**Start Frontend (port 3001):**
```bash
cd fronted
npm start
```

**Access the Application:**
- Frontend URL: http://localhost:3001
- Backend API: http://localhost:8001
- API Documentation: http://localhost:8001/docs
- Health Check: http://localhost:8001/health

### Building Frontend

```bash
cd fronted
npm run build
```

## Backend Architecture (FastAPI)

### Application Structure

The backend follows FastAPI best practices with lifespan-managed dependencies:

**Entry Points:**
- `backend/__main__.py` - Enables `python -m backend` execution
- `backend/app/main.py` - `create_app()` function that configures FastAPI app
- `backend/app/dependencies.py` - `create_dependencies()` creates dependency injection container

**Dependency Injection:**
```python
@dataclass
class AppDependencies:
    user_store: UserStore
    kb_store: KbStore
    ragflow_service: RagflowService
    user_kb_permission_store: UserKbPermissionStore
    deletion_log_store: DeletionLogStore
    download_log_store: DownloadLogStore
```

Dependencies are stored in `app.state.deps` and accessed via `get_deps()` function in each router.

### Router Organization

API endpoints are organized into domain-specific routers:

| Router | Purpose | Key Endpoints |
|-----------|---------|---------------|
| `api/auth.py` | Authentication | `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`, `/api/auth/me` |
| `api/users.py` | User management | `/api/users` (CRUD) |
| `api/knowledge.py` | Document upload | `/api/knowledge/upload`, `/api/knowledge/documents`, `/api/knowledge/stats` |
| `api/review.py` | Document review | `/api/knowledge/documents/{id}/approve`, `/api/knowledge/documents/{id}/reject` |
| `api/ragflow.py` | RAGFlow integration | `/api/ragflow/datasets`, `/api/ragflow/documents`, `/api/ragflow/download` |
| `api/user_kb_permissions.py` | KB permissions | `/api/user-kb-permissions` |

Routers access dependencies via the unified `AuthContextDep` dependency (see `backend/app/core/authz.py`).

### Authentication Layer

**AuthX Integration** (`core/security.py`):
- JWT-based authentication with access and refresh tokens
- Token storage in httpOnly cookies + Authorization header
- Access token expiration: 15 minutes
- Refresh token expiration: 7 days
- Token payload: `sub` (user_id), `scopes`, `exp`

**Business Authorization**
- JWT `scopes` are kept for compatibility only.
- Business permissions are resolver/permission-group based (see `backend/app/core/permission_resolver.py`).

**Token Endpoints:**
- `POST /api/auth/login` - Returns access_token and refresh_token, sets cookies
- `POST /api/auth/refresh` - Refresh access token using refresh token
- `POST /api/auth/logout` - Clears cookies
- `GET /api/auth/me` - Returns current user info with scopes

### Authorization Layer

**Permission Checking**
- Backend resolves a `PermissionSnapshot` per request and enforces it in routers.
- KB permissions are canonicalized to RAGFlow `dataset_id` when possible (with `kb_name` for display).
- Chat permissions are canonicalized to `chat_<id>` / `agent_<id>` refs.

### Data Layer

**SQLite Database:** `backend/data/auth.db`

**Tables:**
- `users` - User accounts (includes legacy `group_id` for compatibility)
- `permission_groups` - Resolver permission groups (resources + can_* flags)
- `user_permission_groups` - User ↔ permission group mapping (for `group_ids`)
- `kb_documents` - Local uploads/review records (includes `kb_dataset_id` + `kb_name`)
- `user_kb_permissions` - Per-user KB grants (canonicalized refs + `kb_dataset_id` + `kb_name`)
- `user_chat_permissions` - Per-user chat grants (canonicalized `chat_/agent_` refs)
- `chat_sessions` - Local session tracking
- `deletion_logs` - Deletion audit (includes `kb_dataset_id` + `kb_name`)
- `download_logs` - Download audit (includes `kb_dataset_id` + `kb_name`)

**Data Stores** (Repository Pattern):
- `services/user_store.py` - User CRUD, password hashing (SHA256), login tracking
- `services/kb_store.py` - Document metadata, status tracking, statistics
- `services/ragflow_service.py` - RAGFlow API integration
- `services/user_kb_permission_store.py` - KB permission management
- `services/deletion_log_store.py` - Deletion audit logging
- `services/download_log_store.py` - Download audit logging

**Password Hashing:**
- SHA256 without salt (for simplicity)
- Function: `hashlib.sha256(password.encode()).hexdigest()`

### Security Features

- **Password Hashing:** SHA256
- **JWT Tokens:** Short-lived access tokens (15 min) + long-lived refresh tokens (7 days)
- **httpOnly Cookies:** Prevents XSS attacks on tokens
- **CORS:** Configurable origins (default: `*` for development)
- **File Validation:** Type whitelist (.txt, .pdf, .doc, .docx, .md), size limit (16MB)
- **Audit Logging:** Deletion and download logs for compliance

## Frontend Architecture

### React Router v6 Structure

**Entry Point:** `fronted/src/App.js` - Main routing with AuthProvider wrapper

**Routes:**
| Path | Component | Permission Required |
|------|-----------|---------------------|
| `/login` | `LoginPage` | None |
| `/` | `Dashboard` | None (shows stats based on permissions) |
| `/users` | `UserManagement` | `users:view` |
| `/upload` | `KnowledgeUpload` | `kb_documents:upload` |
| `/documents` | `DocumentReview` | `kb_documents:view` |
| `/browser` | `DocumentBrowser` | `ragflow_documents:view` |
| `/unauthorized` | `Unauthorized` | None |

### State Management

**Context API:**
- `AuthProvider` (context/AuthContext.js) - Provides authentication state
- `useAuth` hook - Manages login/logout, token storage, user data, permissions

**Permission System:**
- Permission caching to reduce API calls
- Helper methods: `isAdmin()`, `isReviewer()`, `isOperator()`, `hasPermission()`
- Automatic token refresh and logout on expiry

**Route Protection:**
- `PermissionGuard` component - HOC for protecting routes based on permissions
- Redirects to `/unauthorized` if permission check fails
- Supports both role-based and permission-based access control

### API Client

**authClient** (`src/api/authClient.js`):
Centralized API client with automatic authorization headers

**Methods:**
- Authentication: `login()`, `logout()`, `getCurrentUser()`
- User Management: `listUsers()`, `createUser()`, `updateUser()`, `deleteUser()`
- Documents: `uploadDocument()`, `listDocuments()`, `approveDocument()`, `rejectDocument()`
- RAGFlow: `listDatasets()`, `listDatasetDocuments()`, `downloadDocument()`, `downloadBatch()`

**Error Handling:**
- User-friendly error messages
- Automatic 401 redirect to login
- Confirmation dialogs for destructive actions

### Key Components

**Layout System:**
- `components/Layout.js` - Sidebar navigation with collapsible menu
- Dynamic navigation based on user permissions
- Responsive design with user info display

**Pages:**
- `pages/LoginPage.js` - Login form with error handling
- `pages/Dashboard.js` - Home with statistics and quick actions
- `pages/UserManagement.js` - User CRUD operations
- `pages/KnowledgeUpload.js` - Document upload with progress tracking
- `pages/DocumentReview.js` - Document approval/rejection workflow
- `pages/DocumentBrowser.js` - Browse RAGFlow documents

## Integration with RagInt

### RAGFlow Integration

The Auth system integrates with RAGFlow for knowledge base management:

**Ragflow Service** (`services/ragflow_service.py`):
- Uses `ragflow-sdk` for RAGFlow API calls
- Configuration from repo root `ragflow_config.json`
- Document synchronization between local review workflow and RAGFlow

**Document Workflow:**
1. User uploads document → Stored in `backend/data/uploads/` (default; controlled by `UPLOAD_DIR`)
2. Document marked as "pending" in local database
3. Reviewer approves/rejects document via review interface
4. Approved documents synced to RAGFlow knowledge base
5. Documents can be browsed and downloaded from RAGFlow
6. All deletions and downloads are logged for audit purposes

### Port Allocation

| Service | Port | Purpose |
|---------|------|---------|
| Auth Backend (FastAPI) | 8001 | Auth API |
| Auth Frontend | 3001 | Auth UI |
| RagInt Backend | 8000 | Main system API |
| RagInt Frontend | 3000 | Main system UI |

### Environment Configuration

**Frontend (.env):**
```
REACT_APP_AUTH_URL=http://localhost:8001
```

**Backend Configuration** (`backend/app/core/config.py` and `backend/config.py`):
- All settings use pydantic-settings BaseSettings
- Database path: `data/auth.db` (relative to `backend/`)
- Upload directory: `data/uploads/` (relative to `backend/`)
- JWT secret, token expiration, CORS origins configurable via env vars
- Create `.env` file in `backend/` for production settings

## Common Development Tasks

### Adding a New API Endpoint

1. Create router file in `backend/api/your_feature.py`:
   ```python
   from fastapi import APIRouter, Depends
   from core.security import auth

   router = APIRouter()

   def get_deps(request: Request) -> AppDependencies:
       return request.app.state.deps

   @router.post("/api/your-endpoint")
   async def your_endpoint(
       request: Request,
       deps: AppDependencies = Depends(get_deps)
   ):
       # Access deps.user_store, deps.kb_store, etc.
       return {"ok": True}
   ```

2. Register in `backend/app/main.py:create_app()`:
   ```python
   from api import your_feature
   app.include_router(your_feature.router, prefix="/api", tags=["Your Feature"])
   ```

### Adding a New Scope

Scopes are not used for business authorization in this project.
Business permissions are resolver/permission-group based (see `backend/app/core/permission_resolver.py`).

### Creating a New Frontend Page

1. Create page component in `fronted/src/pages/YourPage.js`
2. Add route in `fronted/src/App.js`:
   ```jsx
   <Route path="/yourpage" element={
     <PermissionGuard permission="your_resource:view">
       <YourPage />
     </PermissionGuard>
   } />
   ```
3. Add navigation link in `components/Layout.js` if needed

### Database Migration

**Migrations are in `backend/migrations/` directory:**
- Example: `migrations/migrate_user_kb_permissions.py`

**To run a migration:**
```bash
cd backend
python migrations/migrate_your_migration.py
```

**To create a new migration:**
1. Create Python script in `migrations/`
2. Connect to database using `sqlite3.connect(db_path)`
3. Execute ALTER TABLE or other SQL commands
4. Commit changes and close connection

## Database Initialization

**Initialization Script:** `backend/database/init_db.py`

Creates:
1. SQLite database with all tables
2. Default admin user (username: `admin`, password: `admin123`)
3. Required directories (data, uploads)

**Re-initialization:**
```bash
# Backup existing data first
cp backend/data/auth.db backend/data/auth.db.backup

# Re-run initialization
cd backend
python -m database.init_db
```

## Technology Stack

**Backend (FastAPI):**
- FastAPI >= 0.109.0 - Modern web framework
- Uvicorn >= 0.27.0 - ASGI server
- AuthX >= 1.2.0 - JWT authentication
- Pydantic >= 2.5.0 - Data validation
- pydantic-settings >= 2.1.0 - Configuration management
- ragflow-sdk >= 0.12.0 - RAGFlow integration
- python-multipart >= 0.0.6 - File upload support

**Frontend:**
- React 18.2.0 - UI framework
- React Router DOM 6.20.0 - Routing
- Axios 1.6.0 - HTTP client
- React Scripts 5.0.1 - Build tool

## File Naming Convention

**Important:** The frontend directory is `fronted/` (not `frontend/`) - maintain this naming convention throughout the codebase.

## Architecture Patterns

1. **FastAPI App Factory:** `create_app()` for application creation with lifespan context manager
2. **Dependency Injection:** `AppDependencies` container stored in `app.state.deps`
3. **Router Pattern:** FastAPI routers for modular API organization by domain
4. **Repository Pattern:** Data stores abstract database operations
5. **Pydantic Models:** Request/response validation with automatic OpenAPI docs
6. **Context API:** Centralized authentication state in React
7. **Custom Hooks:** Encapsulate business logic (useAuth)
8. **Resolver-based Authorization:** Business permissions are computed per request from permission groups (JWT scopes are compat-only)

## Security Considerations

- **JWT Access Tokens:** 15-minute expiration for security
- **JWT Refresh Tokens:** 7-day expiration for convenience
- **httpOnly Cookies:** Tokens stored in httpOnly cookies prevent XSS access
- **SHA256 Password Hashing:** No salt (simplicity trade-off)
- **CORS:** Configurable origins (default `*` for development)
- **File Validation:** Type whitelist and size limits
- **Audit Logging:** Deletion and download logs for compliance
- **Stateless Authentication:** JWT-based auth (authorization is resolver-based, not scopes-based)
