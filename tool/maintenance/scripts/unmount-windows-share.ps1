# Windows Share Unmount Script
# Function: Unmount /mnt/replica Windows share

$LogFile = "C:\Users\BJB110\AppData\Local\Temp\unmount_windows_share.log"

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$Timestamp] $Message" | Out-File -FilePath $LogFile -Append -Encoding UTF8
    Write-Host "[$Timestamp] $Message"
}

function Invoke-SSH {
    param([string]$Command)
    $EscapedCommand = $Command.Replace('"', '\"')
    $FullCommand = "ssh -o BatchMode=yes -o ConnectTimeout=10 -o ControlMaster=no root@172.30.30.57 ""$EscapedCommand"""
    Write-Log "Execute: $Command"
    $Output = Invoke-Expression $FullCommand 2>&1
    $ExitCode = $LASTEXITCODE
    Write-Log "Exit Code: $ExitCode"
    if ($Output -and $Output.Length -gt 500) {
        $Truncated = $Output.Substring(0, 500)
        Write-Log "Output: $Truncated"
    } elseif ($Output) {
        Write-Log "Output: $Output"
    }
    return [PSCustomObject]@{
        Output = $Output
        ExitCode = if ($ExitCode -ne $null) { $ExitCode } else { 0 }
    }
}

try {
    Write-Log "========================================"
    Write-Log "Start Unmounting Windows Share"
    Write-Log "========================================"

    # Step 1: Stop backend container
    Write-Log ""
    Write-Log "[Step 1] Stop backend container"

    $Result = Invoke-SSH "docker stop ragflowauth-backend 2>/dev/null; exit 0"
    Write-Log "Success: Backend container stopped"

    Start-Sleep -Seconds 2

    # Step 2: Unmount network share
    Write-Log ""
    Write-Log "[Step 2] Unmount network share"

    $Result = Invoke-SSH "umount /mnt/replica 2>&1"

    if ($Result.ExitCode -eq 0) {
        Write-Log "Success: Unmounted successfully"
    } elseif ($Result.Output -match "not mounted") {
        Write-Log "Info: Was not mounted"
    } else {
        Write-Log "Warning: Unmount returned - $($Result.Output)"
    }

    # Step 3: Restart backend container
    Write-Log ""
    Write-Log "[Step 3] Restart backend container"

    $Result = Invoke-SSH "docker start ragflowauth-backend"
    Write-Log "Success: Backend container restarted"

    # Step 4: Verify unmount
    Write-Log ""
    Write-Log "[Step 4] Verify unmount status"

    $Result = Invoke-SSH "mount | grep replica; exit 0"

    if ($Result.Output -match "replica" -or $Result.Output -match "192.168.112.72") {
        Write-Log "[ERROR] Still shows mounted status - $($Result.Output)"
        Write-Log "========================================"
        Write-Log "[FAILED] Unmount verification failed"
        Write-Log "========================================"
        exit 1
    }

    Write-Log "Success: Confirmed unmounted"

    Write-Log ""
    Write-Log "========================================"
    Write-Log "[SUCCESS] Windows Share Unmounted!"
    Write-Log "========================================"

    exit 0

} catch {
    Write-Log "[Exception] $_"
    Write-Log "========================================"
    Write-Log "[FAILED] Unmount process error"
    Write-Log "========================================"
    exit 1
}
