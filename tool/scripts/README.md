# Tool Scripts Directory

This directory contains deployment and backup scripts for RagflowAuth.

## Deployment Scripts

### deploy.ps1
Main PowerShell deployment script for Windows. Builds Docker images, exports them, and deploys to remote server.

**Usage:**
```powershell
# Basic deployment (uses defaults from deploy-config.json)
.\deploy.ps1

# With custom parameters
.\deploy.ps1 -Tag "v1.0.0" -ServerHost "172.30.30.57" -ServerUser "root"

# Skip certain steps
.\deploy.ps1 -SkipBuild -SkipTransfer  # Only deploy existing images
```

**Parameters:**
- `-Tag`: Docker image tag (default: current date)
- `-ServerHost`: Target server IP (default: 172.30.30.57)
- `-ServerUser`: SSH username (default: root)
- `-SkipBuild`: Skip building images
- `-SkipTransfer`: Skip transferring images to server
- `-SkipDeploy`: Skip server deployment
- `-SkipCleanup`: Skip cleanup prompt
- `-OutDir`: Output directory for exported images (default: dist)

### deploy-quick.bat
Double-click to run deployment with default settings. Simplified interface for quick deployments.

### deploy-config.json
Default configuration file containing:
- Server connection settings (host, user, port)
- Docker settings (tag, ports, network)
- RAGFlow configuration (API key, base URL)

### remote-deploy.sh
Server-side Bash script that:
- Loads Docker images
- Creates containers with proper volumes
- Sets up networks
- Configures data directories

Executed automatically by `deploy.ps1` on the remote server.

## Backup & Restore Scripts

### Download Scripts
- `Download-Backup.bat/ps1`: Downloads latest backup pack (incremental or full)
- `Download-FullBackup.bat/ps1`: Downloads latest full backup pack specifically

### Restore Script
- `Restore-RagflowBackup.ps1`: Automated restore from downloaded backup pack

## Documentation

- `DEPLOY.md`: Complete deployment guide with troubleshooting
- `DEPLOY-TOOLS-README.md`: Quick start guide for deployment tools
- `RESTORE-GUIDE.md`: Detailed backup restore procedures

## Quick Reference

**Deploy to production server (172.30.30.57):**
```powershell
cd tool/scripts
.\deploy.ps1
```

**Download latest backup from server:**
```powershell
cd tool/scripts
.\Download-Backup.bat
```

**Restore from backup:**
```powershell
cd tool/scripts
.\Restore-RagflowBackup.ps1
```

## Production Server

- **IP**: 172.30.30.57
- **User**: root
- **Default paths**: `/opt/ragflowauth/`

## Notes

- All paths in this directory are relative to the project root
- The scripts assume Docker Desktop is running locally
- SSH access to the production server is required
- Ensure OpenSSH Client is installed on Windows
