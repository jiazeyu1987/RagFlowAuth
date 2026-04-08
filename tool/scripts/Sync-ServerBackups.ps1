param(
    [string]$Server = '172.30.30.57',
    [string]$ServerUser = 'root',
    [int]$SshPort = 22,
    [string]$RemotePath = '/opt/ragflowauth/backups',
    [string]$LocalPath = 'D:\Backups\RagflowAuth\from-test-server',
    [switch]$LatestOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$LogPath = 'D:\ProjectPackage\RagflowAuth\tool\scripts\server-backup-sync.log'

New-Item -ItemType Directory -Force -Path $LocalPath | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $LogPath) | Out-Null

function Write-Log {
    param([Parameter(Mandatory)][string]$Message)

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogPath -Value $line
}

function Get-PreferredCommand {
    param([Parameter(Mandatory)][string]$Name)

    $preferred = Get-Command $Name -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -like '*Windows*' -or $_.Source -like '*System32*' } |
        Select-Object -First 1
    if ($preferred) {
        return $preferred
    }

    return Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Invoke-SshCapture {
    param(
        [Parameter(Mandatory)]$SshCommand,
        [Parameter(Mandatory)][string]$RemoteCommand
    )

    $args = @(
        '-q'
        '-o', 'StrictHostKeyChecking=no'
        '-o', 'UserKnownHostsFile=NUL'
        '-p', $SshPort
        "${ServerUser}@${Server}"
        $RemoteCommand
    )
    $output = & $SshCommand.Source @args 2>&1
    $exitCode = $LASTEXITCODE
    return [PSCustomObject]@{
        ExitCode = $exitCode
        Output   = ($output | Out-String).Trim()
    }
}

function Get-RemoteBackupNames {
    param([Parameter(Mandatory)]$SshCommand)

    $remoteCommand = "cd '$RemotePath' 2>/dev/null && for d in *_pack_*; do [ -d ""`$d"" ] && printf '%s\n' ""`$d""; done | sort"
    $result = Invoke-SshCapture -SshCommand $SshCommand -RemoteCommand $remoteCommand
    if ($result.ExitCode -ne 0) {
        throw "failed_to_list_remote_backups:$($result.Output)"
    }

    $names = @()
    foreach ($line in ($result.Output -split "`r?`n")) {
        $name = ($line | Out-String).Trim()
        if (-not $name) {
            continue
        }
        if ($name -like 'migration_pack_*' -or $name -like 'full_backup_pack_*') {
            $names += $name
        }
    }

    return @($names | Sort-Object)
}

function Copy-BackupFromServer {
    param(
        [Parameter(Mandatory)]$ScpCommand,
        [Parameter(Mandatory)][string]$BackupName,
        [Parameter(Mandatory)][string]$TempRoot
    )

    $source = "${ServerUser}@${Server}:${RemotePath}/${BackupName}"
    $args = @(
        '-q'
        '-r'
        '-P', $SshPort
        '-o', 'StrictHostKeyChecking=no'
        '-o', 'UserKnownHostsFile=NUL'
        $source
        $TempRoot
    )

    & $ScpCommand.Source @args
    if ($LASTEXITCODE -ne 0) {
        throw "download_failed:$BackupName"
    }
}

Write-Log '========== server backup sync start =========='
Write-Log "server=$Server"
Write-Log "remote_path=$RemotePath"
Write-Log "local_path=$LocalPath"
Write-Log ("mode=" + ($(if ($LatestOnly) { 'latest_only' } else { 'all_missing' })))

$tempRoot = $null

try {
    $sshCmd = Get-PreferredCommand -Name 'ssh'
    $scpCmd = Get-PreferredCommand -Name 'scp'
    if (-not $sshCmd -or -not $scpCmd) {
        throw 'ssh_or_scp_not_found'
    }

    Write-Log "ssh=$($sshCmd.Source)"
    Write-Log "scp=$($scpCmd.Source)"

    $testResult = Invoke-SshCapture -SshCommand $sshCmd -RemoteCommand "echo connected"
    if ($testResult.ExitCode -ne 0 -or $testResult.Output -ne 'connected') {
        throw "ssh_connect_test_failed:$($testResult.Output)"
    }

    $remoteNames = Get-RemoteBackupNames -SshCommand $sshCmd
    if (-not $remoteNames -or $remoteNames.Count -eq 0) {
        throw "no_remote_backups_found:$RemotePath"
    }

    if ($LatestOnly) {
        $remoteNames = @($remoteNames | Select-Object -Last 1)
    }

    $missingNames = New-Object System.Collections.Generic.List[string]
    foreach ($name in $remoteNames) {
        $localDir = Join-Path $LocalPath $name
        if (Test-Path $localDir) {
            Write-Log "skip_existing=$name"
            continue
        }
        $missingNames.Add($name)
    }

    if ($missingNames.Count -eq 0) {
        Write-Log 'no_missing_backups'
        Write-Log '========== server backup sync complete =========='
        exit 0
    }

    $tempRoot = Join-Path $env:TEMP ("ragflow_server_backup_sync_" + (Get-Date -Format 'yyyyMMdd_HHmmss'))
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    Write-Log "temp_root=$tempRoot"

    $downloaded = New-Object System.Collections.Generic.List[string]
    foreach ($name in $missingNames) {
        Write-Log "download_start=$name"
        Copy-BackupFromServer -ScpCommand $scpCmd -BackupName $name -TempRoot $tempRoot

        $tempDir = Join-Path $tempRoot $name
        if (-not (Test-Path $tempDir)) {
            throw "downloaded_dir_not_found:$tempDir"
        }

        Move-Item -Path $tempDir -Destination $LocalPath -Force
        $downloaded.Add($name)
        Write-Log "download_done=$(Join-Path $LocalPath $name)"
    }

    Write-Log "download_count=$($downloaded.Count)"
    foreach ($name in $downloaded) {
        Write-Log "synced=$name"
    }
    Write-Log '========== server backup sync complete =========='
}
catch {
    Write-Log "error=$($_.Exception.Message)"
    Write-Log '========== server backup sync failed =========='
    exit 1
}
finally {
    if ($tempRoot -and (Test-Path $tempRoot)) {
        Remove-Item -Path $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
