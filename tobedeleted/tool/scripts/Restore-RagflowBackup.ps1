# RagflowAuth Backup Restore Script
# Purpose: Restore backup from local to Linux server

param(
    [Parameter(Mandatory = $false)]
    [string]$BackupPath = (Get-ChildItem -Path "D:\datas" -Filter "migration_pack_*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
)

# Configuration
$Server       = '172.30.30.57'
$ServerUser   = 'root'
$SshPort      = 22
$RemoteBase   = '/opt/ragflowauth/data/backups'
$LogPath      = 'D:\ProjectPackage\RagflowAuth\tool\scripts\backup-restore.log'

# Create log directory
New-Item -ItemType Directory -Force -Path (Split-Path $LogPath) | Out-Null

function Write-Log {
    param([Parameter(Mandatory)][string]$Message)

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
    Add-Content -Path $LogPath -Value $logMessage
}

Write-Log '========== Starting Backup Restore Task =========='

# Check backup path
if (-not $BackupPath) {
    throw "No backup found. Please specify -BackupPath parameter or ensure migration_pack_* exists in D:\datas"
}

if (-not (Test-Path $BackupPath)) {
    throw "Backup path does not exist: $BackupPath"
}

$backupName = Split-Path $BackupPath -Leaf
Write-Log "Backup package: $backupName"
Write-Log "Local path: $BackupPath"

# Check backup contents
Write-Log 'Checking backup contents...'
$manifestPath = Join-Path $BackupPath "manifest.json"
if (-not (Test-Path $manifestPath)) {
    throw "manifest.json not found, backup may be corrupted"
}

$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
Write-Log "Backup created at: $($manifest.created_at)"
Write-Log "Contains: auth.db=$($manifest.contains.auth_db), ragflow=$($manifest.contains.ragflow)"

try {
    # Test server connection
    Write-Log "Testing server connection (SSH port $SshPort)..."
    $portOk = $false
    if (Get-Command Test-NetConnection -ErrorAction SilentlyContinue) {
        $portOk = Test-NetConnection -ComputerName $Server -Port $SshPort -InformationLevel Quiet
    }
    else {
        Write-Log 'Test-NetConnection not found, using ICMP Ping...'
        $portOk = Test-Connection -ComputerName $Server -Count 2 -Quiet
    }
    if (-not $portOk) {
        throw "Cannot connect to server ${Server}:$SshPort"
    }
    Write-Log 'Server connected successfully'

    # Find SCP command
    Write-Log 'Checking scp command...'
    $scpCmd = Get-Command scp -ErrorAction SilentlyContinue
    if (-not $scpCmd) {
        throw 'scp command not found. Please install OpenSSH Client.'
    }
    Write-Log "scp available: $($scpCmd.Source)"

    # Upload backup to server
    Write-Log "Uploading backup to server..."
    $remotePath = "$RemoteBase/$backupName"

    # Upload using SCP
    $scpArgs = @(
        '-q'
        '-r'
        '-P', $SshPort
        '-o', 'StrictHostKeyChecking=no'
        '-o', 'UserKnownHostsFile=NUL'
        $BackupPath
        "${ServerUser}@${Server}:${RemoteBase}"
    )

    Write-Log "Executing: $($scpCmd.Source) $($scpArgs -join ' ')"

    $errorOutput = ""
    try {
        & $scpCmd.Source @scpArgs 2>&1 | Tee-Object -Variable output | Out-Null
        $exitCode = $LASTEXITCODE
    } catch {
        $errorOutput = $_.Exception.Message
        $exitCode = -1
    }

    if ($exitCode -ne 0) {
        Write-Log "SCP exit code: $exitCode"
        if ($output) {
            Write-Log "Output: $($output -join [Environment]::NewLine)"
        }
        Write-Log "Error: $errorOutput"
        throw "SCP upload failed, exit code: $exitCode"
    }

    Write-Log 'Backup upload completed'

    # Execute restore on server
    Write-Log 'Starting data restore...'

    # Step 1: Stop backend container (to release database lock)
    Write-Log 'Stopping backend container...'
    $sshCmd = Get-Command ssh -ErrorAction SilentlyContinue
    $stopCmd = "docker stop ragflowauth-backend || true"
    $sshArgs = @('-q', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=NUL', '-p', $SshPort, "${ServerUser}@${Server}", $stopCmd)
    $stopOutput = & $sshCmd.Source @sshArgs 2>&1
    $stopOutput | ForEach-Object { Write-Log $_ }

    # Step 2: Restore auth.db
    Write-Log 'Restoring auth.db...'
    $authRestoreCmd = "cp '${remotePath}/auth.db' '/opt/ragflowauth/data/auth.db'; echo 'auth.db restored'"
    $sshArgs = @('-q', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=NUL', '-p', $SshPort, "${ServerUser}@${Server}", $authRestoreCmd)
    $authOutput = & $sshCmd.Source @sshArgs 2>&1
    $authOutput | ForEach-Object { Write-Log $_ }

    # Step 3: Start backend container
    Write-Log 'Starting backend container...'
    $startCmd = "docker start ragflowauth-backend"
    $sshArgs = @('-q', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=NUL', '-p', $SshPort, "${ServerUser}@${Server}", $startCmd)
    $startOutput = & $sshCmd.Source @sshArgs 2>&1
    $startOutput | ForEach-Object { Write-Log $_ }

    # Step 4: Restore RAGFlow volumes
    Write-Log 'Restoring RAGFlow volumes...'

    # List volume files and restore each one
    $volumesDir = Join-Path $BackupPath "ragflow\volumes"
    $volumeFiles = Get-ChildItem -Path $volumesDir -Filter "*.tar.gz"

    foreach ($volFile in $volumeFiles) {
        $fileName = $volFile.Name
        # Extract volume name (remove timestamp and extension)
        $volName = ($fileName -replace '_\d{8}_\d{6}\.tar\.gz$', '')

        Write-Log "Restoring volume: $volName from $fileName"

        # Build restore command
        $restoreCmd = "docker run --rm -v '${volName}:/volume_data' -v '${remotePath}/ragflow/volumes:/backup:ro' ragflowauth-backend:local sh -c 'rm -rf /volume_data/* /volume_data/.??* 2>/dev/null; tar -xzf /backup/${fileName} -C /volume_data'"

        $sshArgs = @('-q', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=NUL', '-p', $SshPort, "${ServerUser}@${Server}", $restoreCmd)
        $volOutput = & $sshCmd.Source @sshArgs 2>&1
        $volOutput | ForEach-Object { Write-Log $_ }

        Write-Log "OK $volName restored"
    }

    Write-Log "OK All volumes restored"

    # Step 5: Restart RAGFlow services to reload restored data
    Write-Log 'Restarting RAGFlow services to reload restored data...'
    $restartCmd = "cd /opt/ragflowauth/ragflow_compose && docker compose restart"
    $sshArgs = @('-q', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=NUL', '-p', $SshPort, "${ServerUser}@${Server}", $restartCmd)
    $restartOutput = & $sshCmd.Source @sshArgs 2>&1
    $restartOutput | ForEach-Object { Write-Log $_ }

    Write-Log 'OK RAGFlow services restarted'

    Write-Log '========== Backup Restore Completed =========='
    Write-Log "Backup restored from $BackupPath to server"
    Write-Log 'RAGFlow services have been restarted and are loading restored data.'
    Write-Log 'Next steps:'

    $step1 = "1. Verify auth.db: ssh root@${Server} 'sqlite3 /opt/ragflowauth/data/auth.db .tables'"
    $step2 = "2. Verify RAGFlow services: ssh root@${Server} 'cd /opt/ragflowauth/ragflow_compose && docker compose ps'"
    $step3 = "3. Check RAGFlow logs: ssh root@${Server} 'cd /opt/ragflowauth/ragflow_compose && docker compose logs --tail=50'"

    Write-Host $step1
    Write-Host $step2
    Write-Host $step3

    Write-Log $step1
    Write-Log $step2
    Write-Log $step3

    Write-Log 'SUCCESS: Backup restore completed successfully'
    exit 0

}
catch {
    $errorMsg = if ($_.Exception.Message) { $_.Exception.Message } else { $_.Exception.ToString() }
    Write-Log "Error: $errorMsg"
    Write-Log 'Task failed'
    exit 1
}
