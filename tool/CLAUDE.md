# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Production Server

- **IP Address**: `172.30.30.57`
- **Username**: `root`
- **Description**: Remote Linux server where RagflowAuth is deployed via Docker

When user mentions "服务器" or "远程服务器", they refer to this server.

## Tool Directory (tool/)

This directory contains deployment automation tools and utilities for RagflowAuth. These are Windows-focused PowerShell and Python scripts for building, packaging, deploying, and maintaining RagflowAuth installations.

### Directory Structure

```
tool/
├── scripts/                    # Deployment and backup scripts
│   ├── deploy.ps1             # Main deployment script
│   ├── deploy-quick.bat       # Quick deployment launcher
│   ├── deploy-config.json     # Default deployment config
│   ├── remote-deploy.sh       # Server-side deployment script
│   ├── Download-Backup.bat/ps1    # Backup download scripts
│   ├── Download-FullBackup.bat/ps1 # Full backup download
│   ├── Restore-RagflowBackup.ps1   # Backup restore script
│   └── DEPLOY.md              # Deployment documentation
└── 无用/                      # Legacy UI tools (deprecated)
    ├── release_packager_ui.py      # Release packaging tool
    ├── release_installer_ui.py     # Release installer
    ├── migration_restore_ui.py     # Migration restore tool
    └── setup_backup_share_ui.py    # SMB share configurator
```

### Architecture

The tool directory is organized around three main workflows:

1. **Remote Deployment** (`scripts/deploy.ps1`, `scripts/deploy-quick.bat`, `scripts/remote-deploy.sh`)
   - Builds Docker images locally
   - Exports images to tar files with SHA256 checksums
   - Transfers to remote Linux server via SCP
   - Executes server-side deployment script

2. **Release Packaging** (`无用/release_packager_ui.py`)
   - Creates distributable release ZIP files
   - Bundles auth DB, RAGFlow docker-compose data, and application files
   - Supports local or network share output

3. **Installation & Migration** (`无用/release_installer_ui.py`, `无用/migration_restore_ui.py`)
   - `release_installer_ui.py`: One-click deployment from release ZIP to Docker
   - `migration_restore_ui.py`: Restore backup/migration packs to running system
   - `setup_backup_share_ui.py`: Configure Windows SMB shares for backup

### Key Files

- **scripts/deploy.ps1**: Main deployment script (PowerShell)
  - Usage: `cd tool/scripts && .\deploy.ps1` or `.\deploy.ps1 -Tag "v1.0.0" -ServerHost "192.168.1.100"`
  - Steps: Build → Export → Transfer → Deploy → Cleanup
  - Parameters: `-Tag`, `-ServerHost`, `-ServerUser`, `-SkipBuild`, `-SkipTransfer`, `-SkipDeploy`, `-SkipCleanup`, `-OutDir`

- **scripts/deploy-quick.bat**: Quick launcher (double-click to run)
  - Uses default config from `scripts/deploy-config.json`

- **scripts/deploy-config.json**: Default deployment configuration
  - Server host, user, Docker tag, ports, network settings
  - RAGFlow API key and base URL

- **scripts/remote-deploy.sh**: Server-side deployment script (Bash)
  - Loaded onto remote server and executed via SSH
  - Handles Docker load, container orchestration, network setup
  - Creates data directories and mounts volumes
  - Default server paths: `/opt/ragflowauth/`

### Backup Download & Restore Scripts

Located in `scripts/` subdirectory:

**Download Scripts (Windows):**
- **Download-Backup.bat** / **Download-Backup.ps1**
  - Downloads latest backup pack (incremental or full) from server
  - Automatic selection of most recent backup
  - Output to `D:\datas\` by default
  - Logs to `backup-download.log`

- **Download-FullBackup.bat** / **Download-FullBackup.ps1**
  - Downloads latest full backup pack specifically
  - Used when you need complete system backup
  - Output to `D:\datas\` by default
  - Logs to `full-backup-download.log`

**Restore Scripts:**
- **Restore-RagflowBackup.ps1**
  - Automated restore from downloaded backup pack
  - Uploads backup to server, restores auth.db and RAGFlow volumes
  - Handles all volume restoration automatically
  - Logs to `backup-restore.log`
  - Usage: `.\Restore-RagflowBackup.ps1 [-BackupPath "path"]`

See `scripts/RESTORE-GUIDE.md` for detailed manual restore procedures and disaster recovery scenarios.

### Python UI Tools (Legacy)

Note: These tools are located in `无用/` (unused) subdirectory and may be deprecated:

- **release_packager_ui.py** (v0.3.1) - Creates distributable release ZIP files
- **release_installer_ui.py** (v0.5.0) - One-click deployment from release ZIP
- **migration_restore_ui.py** (v0.2.0) - Restore backup to running system
- **setup_backup_share_ui.py** - Configure Windows SMB shares for backup

### Data Persistence

Server deployment mounts these volumes:
- `/opt/ragflowauth/data` → SQLite auth DB
- `/opt/ragflowauth/uploads` → User uploads
- `/opt/ragflowauth/ragflow_config.json` → RAGFlow configuration (read-only)

### Common Workflows

**Deploy to remote server:**
```powershell
cd tool/scripts
.\deploy.ps1
```

**Build only, skip deployment:**
```powershell
.\deploy.ps1 -SkipTransfer -SkipDeploy -SkipCleanup
```

**Create release package:**
```bash
python tool/无用/release_packager_ui.py
```

**Deploy from release ZIP:**
```bash
python tool/无用/release_installer_ui.py
```

**Restore backup:**
```bash
python tool/无用/migration_restore_ui.py
```

### Configuration Files

- **scripts/deploy-config.json**: Deployment defaults (server, Docker settings, RAGFlow config)
- **ragflow_config.json** (repo root): RAGFlow API connection settings
- **backup_config.json** (repo root, generated by `python -m backend init-backup`): Backup destination settings

### Server Management

After deployment, manage containers via SSH:
```bash
ssh root@<server>

# View containers
docker ps | grep ragflowauth

# View logs
docker logs -f ragflowauth-backend
docker logs -f ragflowauth-frontend

# Restart services
docker restart ragflowauth-backend ragflowauth-frontend

# Update configuration
vi /opt/ragflowauth/ragflow_config.json
docker restart ragflowauth-backend
```

### Troubleshooting

- **Docker connection issues**: Ensure Docker Desktop Linux engine is running
- **SSH connection failures**: Verify OpenSSH client enabled (Windows Settings → Apps → Optional Features)
- **Container startup failures**: Check logs via `docker logs ragflowauth-backend`
- **Port conflicts**: Modify ports in `deploy-config.json` or use `-FrontendPort`/`-BackendPort` parameters

### Related Documentation

- `DISASTER-RECOVERY-ANALYSIS.md`: Comprehensive disaster recovery analysis
  - Covers recovery procedures for various failure scenarios
  - RTO/RPO targets and risk assessment
  - Three-tier backup strategy recommendations
- `scripts/RESTORE-GUIDE.md`: Detailed restore procedures
  - Quick restore with automation scripts
  - Manual restore steps for auth.db and RAGFlow volumes
  - Complete disaster recovery scenarios
- `../CLAUDE.md`: Main project documentation
- `../backend/README.md`: Backend architecture and permission model

### Disaster Recovery Overview

**Backup Strategy:**
- **Incremental backups**: auth.db only (fast, for frequent backups)
- **Full backups**: auth.db + RAGFlow volumes (MySQL, ES, MinIO, Redis)

**Current Limitations:**
- No automated off-site backup (backups stored locally and on server only)
- Docker images not backed up (rebuild required for disaster recovery)
- No system-level snapshots (OS reinstall required for system disk failure)

**Quick Recovery Commands:**
```powershell
# Download latest backup
cd tool/scripts
.\Download-Backup.bat

# Restore from backup
.\Restore-RagflowBackup.ps1
```
