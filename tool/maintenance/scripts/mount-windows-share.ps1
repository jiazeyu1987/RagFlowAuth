# Windows Share Mount Script
# Function: Mount //<WindowsHost>/<ShareName> to <MountPoint> on the selected Linux server via SSH.

param(
    [Parameter(Mandatory = $true)]
    [string]$ServerHost,

    [Parameter(Mandatory = $true)]
    [string]$ServerUser,

    [Parameter(Mandatory = $true)]
    [string]$WindowsHost,

    [Parameter(Mandatory = $true)]
    [string]$ShareName,

    [Parameter(Mandatory = $true)]
    [string]$ShareUsername,

    [Parameter(Mandatory = $true)]
    [string]$SharePassword
)

$LogFile = Join-Path $env:TEMP "mount_windows_share.log"
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

    # Avoid leaking secrets into local logs (credentials may be embedded in the command body).
    $LogCommand = $Command `
        -replace '(?m)^password=.*$', 'password=***' `
        -replace '(?m)^username=.*$', 'username=***'
    Write-Log "Execute: $LogCommand"
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
    Write-Log "Start Mounting Windows Share"
    Write-Log "========================================"

    # Step 1: Check if already mounted
    Write-Log ""
    Write-Log "[Step 1] Check if already mounted"

    # Check CIFS mount (PRIMARY CHECK)
    $Result = Invoke-SSH "mount | grep -E 'type.*cifs|$MountPoint.*type' 2>&1"
    if ($Result.Output -match "type cifs") {
        Write-Log "Detected: Already mounted (CIFS filesystem) - $($Result.Output)"
        Write-Log "Hint: Use 'Unmount Windows Share' first to remount"
        exit 0
    }

    # Check file list (AUXILIARY - can be misleading!)
    $Result2 = Invoke-SSH "timeout 3 ls $MountPoint/$ExpectedSubdir 2>&1; exit 0"
    if ($Result2.Output -match "migration_pack" -and $Result2.Output -notmatch "cannot access" -and $Result2.Output -notmatch "No such file") {
        Write-Log "Warning: Found local backup files but NO CIFS mount detected!"
        Write-Log "Hint: Previous backups may be in local directory, not on Windows share"
        Write-Log "Continuing with mount process..."
    } else {
        Write-Log "Result: Not mounted, starting mount process"
    }

    # Step 2: Create credentials file
    Write-Log ""
    Write-Log "[Step 2] Create credentials file"

    $CredCmd = @"
cat > /root/.smbcredentials << 'EOF'
username=$ShareUsername
password=$SharePassword
EOF
chmod 600 /root/.smbcredentials
"@

    $Result = Invoke-SSH $CredCmd
    if ($Result.ExitCode -ne 0) {
        Write-Log "[ERROR] Failed to create credentials file (Code: $($Result.ExitCode))"
        exit 1
    }
    Write-Log "Success: Credentials file created"

    # Step 3: Stop backend container
    Write-Log ""
    Write-Log "[Step 3] Stop backend container"

    $Result = Invoke-SSH "docker stop ragflowauth-backend 2>/dev/null; exit 0"
    Write-Log "Success: Backend container stopped"

    Start-Sleep -Seconds 2

    # Step 4: Create mount point
    Write-Log ""
    Write-Log "[Step 4] Create mount point"

    $Result = Invoke-SSH "mkdir -p $MountPoint"
    Write-Log "Success: Mount point created"

    # Step 5: Mount CIFS share
    Write-Log ""
    Write-Log "[Step 5] Mount CIFS share"

    $SharePath = "//${WindowsHost}/${ShareName}"
    $MountCmd1 = "mount -t cifs $SharePath $MountPoint -o credentials=/root/.smbcredentials,domain=.,uid=0,gid=0,rw 2>&1"
    $MountCmd2 = "mount -t cifs $SharePath $MountPoint -o credentials=/root/.smbcredentials,domain=.,uid=0,gid=0,rw,vers=3.0,sec=ntlmssp,iocharset=utf8 2>&1"

    $Result = Invoke-SSH $MountCmd1
    if ($Result.ExitCode -ne 0) {
        Write-Log "[ERROR] Mount failed (try#1): $($Result.Output)"
        Write-Log "Retrying with vers=3.0, sec=ntlmssp..."
        $Result = Invoke-SSH $MountCmd2
    }
    if ($Result.ExitCode -ne 0) {
        Write-Log "[ERROR] Mount failed (try#2): $($Result.Output)"

        # Try to start container
        Write-Log "Attempting to start backend container..."
        Invoke-SSH "docker start ragflowauth-backend 2>/dev/null; exit 0"

        Write-Log "========================================"
        Write-Log "[FAILED] Mount failed"
        Write-Log "========================================"
        exit 1
    }

    Write-Log "Success: Mount completed"

    # Step 6: Verify mount
    Write-Log ""
    Write-Log "[Step 6] Verify mount"

    $Result = Invoke-SSH "df -h | grep $MountPoint"
    if ($Result.ExitCode -eq 0 -and $Result.Output) {
        Write-Log "Verify Output: $($Result.Output)"
    } else {
        Write-Log "[WARNING] No disk info retrieved"
    }

    # Step 6.1: Ensure fixed subdir exists
    Write-Log ""
    Write-Log "[Step 6.1] Ensure /mnt/replica/RagflowAuth exists"
    $Result = Invoke-SSH "mkdir -p $MountPoint/$ExpectedSubdir && ls -ld $MountPoint/$ExpectedSubdir 2>&1; exit 0"
    if ($Result.Output) {
        Write-Log "Dir Check: $($Result.Output)"
    }

    # Step 7: Start backend container
    Write-Log ""
    Write-Log "[Step 7] Start backend container"

    $Result = Invoke-SSH "docker start ragflowauth-backend"
    Write-Log "Success: Backend container started"

    # Step 8: Add to /etc/fstab
    Write-Log ""
    Write-Log "[Step 8] Add to /etc/fstab"

    $FstabEntry = "$SharePath $MountPoint cifs credentials=/root/.smbcredentials,domain=.,uid=0,gid=0,rw 0 0"
    $Result = Invoke-SSH "grep -q '$MountPoint' /etc/fstab; if [ `$? -ne 0 ]; then echo '$FstabEntry' >> /etc/fstab; fi"
    Write-Log "Success: Added to /etc/fstab"

    Write-Log ""
    Write-Log "========================================"
    Write-Log "[SUCCESS] Windows Share Mounted!"
    Write-Log "========================================"

    exit 0

} catch {
    Write-Log "[Exception] $_"
    Write-Log "========================================"
    Write-Log "[FAILED] Mount process error"
    Write-Log "========================================"
    exit 1
}
