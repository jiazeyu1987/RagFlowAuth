# Windows Share Mount Script
# Function: Mount //192.168.112.72/backup to /mnt/replica

$LogFile = "C:\Users\BJB110\AppData\Local\Temp\mount_windows_share.log"

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
    Write-Log "Start Mounting Windows Share"
    Write-Log "========================================"

    # Step 1: Check if already mounted
    Write-Log ""
    Write-Log "[Step 1] Check if already mounted"

    $Result = Invoke-SSH "mount | grep /mnt/replica; exit 0"
    if ($Result.Output -match "replica" -or $Result.Output -match "192.168.112.72") {
        Write-Log "Detected: Already mounted - $($Result.Output)"
        Write-Log "Hint: Use 'Unmount Windows Share' first to remount"
        exit 0
    }

    $Result = Invoke-SSH "timeout 3 ls /mnt/replica/RagflowAuth/ 2>&1; exit 0"
    if ($Result.Output -match "migration_pack" -and $Result.Output -notmatch "cannot access" -and $Result.Output -notmatch "No such file") {
        Write-Log "Detected: Already mounted (file access verified)"
        Write-Log "Hint: Use 'Unmount Windows Share' first to remount"
        exit 0
    }

    Write-Log "Result: Not mounted, starting mount process"

    # Step 2: Create credentials file
    Write-Log ""
    Write-Log "[Step 2] Create credentials file"

    $CredCmd = @"
cat > /root/.smbcredentials << 'EOF'
username=BJB110
password=showgood87
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

    $Result = Invoke-SSH "mkdir -p /mnt/replica"
    Write-Log "Success: Mount point created"

    # Step 5: Mount CIFS share
    Write-Log ""
    Write-Log "[Step 5] Mount CIFS share"

    $MountCmd = 'mount -t cifs //192.168.112.72/backup /mnt/replica -o username=BJB110,password=showgood87,domain=.,uid=0,gid=0,rw'

    $Result = Invoke-SSH $MountCmd
    if ($Result.ExitCode -ne 0) {
        Write-Log "[ERROR] Mount failed: $($Result.Output)"

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

    $Result = Invoke-SSH "df -h | grep replica"
    if ($Result.ExitCode -eq 0 -and $Result.Output) {
        Write-Log "Verify Output: $($Result.Output)"
    } else {
        Write-Log "[WARNING] No disk info retrieved"
    }

    # Step 7: Start backend container
    Write-Log ""
    Write-Log "[Step 7] Start backend container"

    $Result = Invoke-SSH "docker start ragflowauth-backend"
    Write-Log "Success: Backend container started"

    # Step 8: Add to /etc/fstab
    Write-Log ""
    Write-Log "[Step 8] Add to /etc/fstab"

    $FstabEntry = '//192.168.112.72/backup /mnt/replica cifs username=BJB110,password=showgood87,domain=.,uid=0,gid=0,rw 0 0'
    $Result = Invoke-SSH "grep -q '/mnt/replica' /etc/fstab; if [ `$? -ne 0 ]; then echo '$FstabEntry' >> /etc/fstab; fi"
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
