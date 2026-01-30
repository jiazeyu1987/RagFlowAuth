# Windows Share Status Check Script
# Function: Check /mnt/replica mount status

param(
    [Parameter(Mandatory = $true)]
    [string]$ServerHost,

    [Parameter(Mandatory = $true)]
    [string]$ServerUser,

    [Parameter(Mandatory = $false)]
    [string]$WindowsHost = ""
)

$LogFile = Join-Path $env:TEMP "check_mount_status.log"
$MountPoint = "/mnt/replica"
$ExpectedSubdir = "RagflowAuth"

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$Timestamp] $Message" | Out-File -FilePath $LogFile -Append -Encoding UTF8
    Write-Host "[$Timestamp] $Message"
}

function Invoke-SSH {
    param([string]$Command)
    $EscapedCommand = $Command.Replace('"', '\"')
    $FullCommand = "ssh -o BatchMode=yes -o ConnectTimeout=10 -o ControlMaster=no $ServerUser@$ServerHost ""$EscapedCommand"""
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

    $TargetDir = "$MountPoint/$ExpectedSubdir"
    $Result = Invoke-SSH "timeout 3 ls $TargetDir 2>&1 | head -1"

    # Check 2: Mount command (PRIMARY - CIFS type check)
    Write-Log ""
    Write-Log "[Check 2] CIFS mount detection"

    $Result2 = Invoke-SSH "mount | grep -E 'type.*cifs|$MountPoint.*type' 2>&1"

    # Determine mount status
    $IsMounted = $false
    $FileListDetected = $false
    $CifsMountDetected = $false

    # Check file list (auxiliary - can be misleading!)
    if ($Result.Output -match "migration_pack" -and $Result.Output -notmatch "cannot access" -and $Result.Output -notmatch "No such file") {
        $FileListDetected = $true
        Write-Log "File List: Detected migration_pack files (but NOT checking mount type)"
    } elseif ($Result.Output -match "cannot access" -or $Result.Output -match "No such file" -or $Result.Output -match "Transport endpoint") {
        Write-Log "File List: Cannot access directory (not mounted or mount failed)"
    } else {
        Write-Log "File List: No migration_pack files detected"
    }

    # Check CIFS mount (PRIMARY CHECK - must be CIFS type)
    if ($Result2.Output -match "type cifs") {
        $CifsMountDetected = $true
        Write-Log "Mount Command: ✓ Detected CIFS mount (type cifs)"
    } else {
        Write-Log "Mount Command: ✗ No CIFS mount found (only local files exist)"
    }

    # Final decision: CIFS mount check has priority
    if ($CifsMountDetected) {
        $IsMounted = $true
        Write-Log "Decision: Mounted (CIFS filesystem detected)"
    } elseif ($FileListDetected) {
        $IsMounted = $false
        Write-Log "Decision: NOT Mounted (local files exist but no CIFS mount)"
        Write-Log "WARNING: Old backup files in local directory can be misleading!"
    } else {
        Write-Log "Result: Not mounted"
    }

    # Check 3: Disk usage
    Write-Log ""
    Write-Log "[Check 3] Disk usage"

    $Result = Invoke-SSH "df -h | grep $MountPoint; exit 0"

    # Check 4: Network connectivity
    Write-Log ""
    Write-Log "[Check 4] Network connectivity"

    $IsReachable = $false
    if ($WindowsHost) {
        $Result = Invoke-SSH "ping -c 1 -W 2 $WindowsHost 2>/dev/null; echo 'unreachable'"
        $IsReachable = $Result.Output -notmatch "unreachable"
    }

    # Check 5: Recent files
    Write-Log ""
    Write-Log "[Check 5] Recent synced files"

    $Result = Invoke-SSH "ls -lt $TargetDir 2>/dev/null | head -10; echo 'DONE'"

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

    if (-not $WindowsHost) {
        Write-Log "Windows Host: (not provided) - skipped ping"
    } elseif ($IsReachable) {
        Write-Log "Windows Host ($WindowsHost): Reachable (OK)"
    } else {
        Write-Log "Windows Host ($WindowsHost): Unreachable"
        Write-Log "Hint: Check network and Windows host power"
    }

    Write-Log ""
    Write-Log "=== Disk Usage ==="

    $Result = Invoke-SSH "df -h | grep $MountPoint; exit 0"
    if ($Result.Output) {
        Write-Log $($Result.Output)
    } else {
        Write-Log "(No mount info)"
    }

    Write-Log ""
    Write-Log "=== Recent Synced Files ==="

    $Result = Invoke-SSH "ls -lt $TargetDir 2>/dev/null | head -10; echo 'DONE'"
    if ($Result.Output -match "DONE" -and $Result.Output.Length -gt 10) {
        $Lines = $Result.Output -split "`n"
        foreach ($Line in $Lines) {
            if ($Line -notmatch "DONE" -and $Line.Trim() -ne "") {
                Write-Log $Line
            }
        }
    } else {
        Write-Log "Cannot access $TargetDir"
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
