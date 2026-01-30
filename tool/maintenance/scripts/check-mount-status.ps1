# Windows Share Status Check Script
# Function: Check /mnt/replica mount status

$LogFile = "C:\Users\BJB110\AppData\Local\Temp\check_mount_status.log"

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
    Write-Log "Check Windows Share Mount Status"
    Write-Log "========================================"

    # Check 1: File list (most reliable)
    Write-Log ""
    Write-Log "[Check 1] File list detection"

    $Result = Invoke-SSH "timeout 3 ls /mnt/replica/RagflowAuth/ 2>&1 | head -1"

    # Check 2: Mount command (auxiliary)
    Write-Log ""
    Write-Log "[Check 2] Mount command detection"

    $Result2 = Invoke-SSH "mount | grep replica; exit 0"

    # Determine mount status
    $IsMounted = $false
    $FileListDetected = $false
    $MountDetected = $false

    # Check file list first (priority)
    if ($Result.Output -match "migration_pack" -and $Result.Output -notmatch "cannot access" -and $Result.Output -notmatch "No such file") {
        $FileListDetected = $true
        Write-Log "File List: Detected migration_pack files -> Mounted"
    } elseif ($Result.Output -match "cannot access" -or $Result.Output -match "No such file" -or $Result.Output -match "Transport endpoint") {
        Write-Log "File List: Cannot access directory (not mounted or mount failed)"
    } else {
        Write-Log "File List: No migration_pack files detected"
    }

    # Check mount command (auxiliary)
    if ($Result2.Output -match "replica" -or $Result2.Output -match "192.168.112.72") {
        $MountDetected = $true
        Write-Log "Mount Command: Detected //192.168.112.72/backup on /mnt/replica"
    } else {
        Write-Log "Mount Command: No mount entry found"
    }

    # Final decision: file list has priority
    if ($FileListDetected) {
        $IsMounted = $true
    } elseif ($MountDetected) {
        $IsMounted = $true
        Write-Log "Decision: Mount detected by mount command"
    } else {
        Write-Log "Result: Not mounted"
    }

    # Check 3: Disk usage
    Write-Log ""
    Write-Log "[Check 3] Disk usage"

    $Result = Invoke-SSH "df -h | grep replica; exit 0"

    # Check 4: Network connectivity
    Write-Log ""
    Write-Log "[Check 4] Network connectivity"

    $Result = Invoke-SSH "ping -c 1 -W 2 192.168.112.72 2>/dev/null; echo 'unreachable'"
    $IsReachable = $Result.Output -notmatch "unreachable"

    # Check 5: Recent files
    Write-Log ""
    Write-Log "[Check 5] Recent synced files"

    $Result = Invoke-SSH "ls -lt /mnt/replica/RagflowAuth/ 2>/dev/null | head -10; echo 'DONE'"

    # Build status report
    Write-Log ""
    Write-Log "========================================"
    Write-Log "Status Report"
    Write-Log "========================================"

    Write-Log ""
    Write-Log "=== Mount Status ==="

    if ($IsMounted) {
        Write-Log "Status: Mounted (OK)"
        if ($Result2.Output) {
            Write-Log "Mount Info: $($Result2.Output)"
        }
    } else {
        Write-Log "Status: Not Mounted"
        Write-Log "Hint: Use 'Mount Windows Share' tool"
    }

    Write-Log ""
    Write-Log "=== Network Connection ==="

    if ($IsReachable) {
        Write-Log "Windows Host (192.168.112.72): Reachable (OK)"
    } else {
        Write-Log "Windows Host (192.168.112.72): Unreachable"
        Write-Log "Hint: Check network and Windows host power"
    }

    Write-Log ""
    Write-Log "=== Disk Usage ==="

    $Result = Invoke-SSH "df -h | grep replica; exit 0"
    if ($Result.Output) {
        Write-Log $($Result.Output)
    } else {
        Write-Log "(No mount info)"
    }

    Write-Log ""
    Write-Log "=== Recent Synced Files ==="

    $Result = Invoke-SSH "ls -lt /mnt/replica/RagflowAuth/ 2>/dev/null | head -10; echo 'DONE'"
    if ($Result.Output -match "DONE" -and $Result.Output.Length -gt 10) {
        $Lines = $Result.Output -split "`n"
        foreach ($Line in $Lines) {
            if ($Line -notmatch "DONE" -and $Line.Trim() -ne "") {
                Write-Log $Line
            }
        }
    } else {
        Write-Log "Cannot access /mnt/replica/RagflowAuth/"
        if (-not $IsMounted) {
            Write-Log "Reason: Share not mounted"
        }
    }

    Write-Log ""
    Write-Log "========================================"
    if ($IsMounted) {
        Write-Log "[Summary] Mount Status: Mounted"
    } else {
        Write-Log "[Summary] Mount Status: Not Mounted"
    }
    Write-Log "========================================"

    exit 0

} catch {
    Write-Log "[Exception] $_"
    Write-Log "========================================"
    Write-Log "[FAILED] Check process error"
    Write-Log "========================================"
    exit 1
}
