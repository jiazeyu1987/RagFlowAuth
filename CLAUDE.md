# RagflowAuth (Codex/Claude Notes)

This repo contains a FastAPI backend and a React frontend for authentication + permission-group-based authorization around RAGFlow.

## Layout

```
RagflowAuth/
├── backend/     # FastAPI backend (port: 8001)
│   ├── app/         # Routers, DI, auth, permission resolver
│   ├── services/    # Stores + RAGFlow clients
│   ├── database/    # SQLite schema + helpers
│   ├── migrations/  # Small migration wrappers (kept for compatibility)
│   ├── scripts/     # One-off maintenance scripts
│   ├── runtime/     # Unified runner (`python -m backend`)
│   └── tests/
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

## Data/Config Conventions

- SQLite DB default: `data/auth.db` (repo root).
- Upload dir default: `data/uploads` (repo root).
- RAGFlow config: `ragflow_config.json` (repo root).

## Authorization Model

- Business permissions are resolved from **permission groups (resolver)**.
- JWT `scopes` are kept for compatibility only and must not drive business authorization.

## Diagnostics

- Permission debug logs are gated by `PERMDBG_ENABLED=true`.
