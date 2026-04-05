# Simple script to create Windows share
# Run as Administrator

Write-Host "Setting up Windows file share..." -ForegroundColor Green

# Check admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Please run as Administrator" -ForegroundColor Red
    pause
    exit 1
}

# Create directory
$path = "D:\datas"
if (-not (Test-Path $path)) {
    Write-Host "Creating directory: $path"
    New-Item -ItemType Directory -Path $path -Force
}

# Enable firewall rules
Write-Host "Enabling firewall rules..."
netsh advfirewall firewall set rule group="File and Printer Sharing" new enable=Yes

# Remove old share if exists
$share = Get-SmbShare -Name "datas" -ErrorAction SilentlyContinue
if ($share) {
    Write-Host "Removing old share..."
    Remove-SmbShare -Name "datas" -Force
}

# Create new share
Write-Host "Creating SMB share..."
New-SmbShare -Name "datas" -Path $path -FullAccess "BJB110","Administrator"

Write-Host ""
Write-Host "SUCCESS! Share created:" -ForegroundColor Green
Write-Host "  Share name: datas"
Write-Host "  Local path: D:\datas"
Write-Host "  Network path: \\192.168.112.72\datas"
Write-Host ""
