# RagflowAuth Deployment Tool
# Purpose: Build, package, transfer and deploy Docker images to remote server

param(
  [Parameter(Mandatory = $false)]
  [string]$Tag = (Get-Date -Format "yyyy-MM-dd"),

  [Parameter(Mandatory = $false)]
  [string]$ServerHost = "172.30.30.57",  # Production server

  [Parameter(Mandatory = $false)]
  [string]$ServerUser = "root",

  [Parameter(Mandatory = $false)]
  [string]$ComposeFile = "docker/docker-compose.yml",

  [Parameter(Mandatory = $false)]
  [switch]$SkipBuild = $false,

  [Parameter(Mandatory = $false)]
  [switch]$SkipTransfer = $false,

  [Parameter(Mandatory = $false)]
  [switch]$SkipDeploy = $false,

  [Parameter(Mandatory = $false)]
  [switch]$SkipCleanup = $false,

  [Parameter(Mandatory = $false)]
  [string]$OutDir = "dist"
)

$ErrorActionPreference = "Stop"

# Output functions
function Write-Step([string]$Message) {
  Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Write-Success([string]$Message) {
  Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Info([string]$Message) {
  Write-Host "  $Message"
}

function Write-Warn([string]$Message) {
  Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

# Check if command exists
function Test-Command([string]$Name) {
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

# Check required tools
Write-Step "Checking required tools"
$requiredTools = @("docker", "scp", "ssh")
$missingTools = @()

foreach ($tool in $requiredTools) {
  if (-not (Test-Command $tool)) {
    $missingTools += $tool
  }
}

if ($missingTools.Count -gt 0) {
  throw "Missing required commands: $($missingTools -join ', ')`nPlease install Docker Desktop and OpenSSH Client"
}

Write-Success "All required tools are installed"

# Setup paths
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ComposeFilePath = Join-Path $RepoRoot $ComposeFile
$OutPath = Join-Path $RepoRoot $OutDir

# Check compose file
if (-not (Test-Path $ComposeFilePath)) {
  throw "Docker compose file not found: $ComposeFilePath"
}

# Create output directory
New-Item -ItemType Directory -Force -Path $OutPath | Out-Null

# ==================== Step 1: Build Images ====================
if (-not $SkipBuild) {
  Write-Step "Step 1/4: Building Docker images (tag=$Tag)"

  Write-Info "Setting environment variable: RAGFLOWAUTH_TAG=$Tag"
  $env:RAGFLOWAUTH_TAG = $Tag

  Write-Info "Building images..."
  docker compose -f $ComposeFilePath build

  if ($LASTEXITCODE -ne 0) {
    throw "Docker image build failed"
  }

  Write-Success "Images built successfully"
} else {
  Write-Step "Skipping image build"
}

# ==================== Step 2: Export Images ====================
Write-Step "Step 2/4: Exporting Docker images"

Write-Info "Resolving image list..."
$images = (docker compose -f $ComposeFilePath config --images) | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() }

if (-not $images -or $images.Count -lt 2) {
  throw "Failed to resolve image list"
}

Write-Info "Found $($images.Count) images:"
$images | ForEach-Object { Write-Info "  - $_" }

$TarName = "ragflowauth-images_$Tag.tar"
$TarPath = Join-Path $OutPath $TarName

Write-Info "Exporting images to: $TarPath"
& docker save -o $TarPath $images

if ($LASTEXITCODE -ne 0) {
  throw "Docker image export failed"
}

# Generate checksum
Write-Info "Generating SHA256 checksum..."
$Hash = Get-FileHash -Algorithm SHA256 -Path $TarPath
$HashPath = "$TarPath.sha256"
("$($Hash.Hash)  $TarName") | Set-Content -Encoding ASCII -NoNewline -Path $HashPath

$TarSize = (Get-Item $TarPath).Length / 1MB
Write-Success "Images exported ($([math]::Round($TarSize, 2)) MB)"

# ==================== Step 3: Transfer to Server ====================
if (-not $SkipTransfer) {
  Write-Step "Step 3/4: Transferring images to server"

  Write-Info "Target server: ${ServerUser}@${ServerHost}"
  Write-Info "Transferring file: $TarName"

  scp $TarPath "${ServerUser}@${ServerHost}:/tmp/"

  if ($LASTEXITCODE -ne 0) {
    throw "File transfer failed"
  }

  Write-Success "File transferred successfully"
} else {
  Write-Step "Skipping file transfer"
}

# ==================== Step 4: Deploy on Server ====================
if (-not $SkipDeploy) {
  Write-Step "Step 4/4: Deploying on server"

  # Upload local configuration file
  $localConfig = Join-Path $RepoRoot "ragflow_config.json"
  if (Test-Path $localConfig) {
    Write-Info "Uploading local ragflow_config.json..."
    $remoteConfigDir = "/opt/ragflowauth"
    ssh "${ServerUser}@${ServerHost}" "mkdir -p $remoteConfigDir"
    scp $localConfig "${ServerUser}@${ServerHost}:${remoteConfigDir}/ragflow_config.json"
    Write-Success "Configuration file uploaded"
  } else {
    Write-Warn "Local ragflow_config.json not found, using remote default"
  }

  # Use the existing remote-deploy.sh script
  $localDeployScript = Join-Path $PSScriptRoot "remote-deploy.sh"

  if (Test-Path $localDeployScript) {
    Write-Info "Uploading deploy script..."
    scp $localDeployScript "${ServerUser}@${ServerHost}:/tmp/remote-deploy.sh"

    Write-Info "Converting line endings..."
    ssh "${ServerUser}@${ServerHost}" "sed -i 's/\r$//' /tmp/remote-deploy.sh"

    Write-Info "Executing remote deploy script..."
    ssh "${ServerUser}@${ServerHost}" "chmod +x /tmp/remote-deploy.sh && TAG=$Tag SKIP_CONFIG_CREATE=1 /tmp/remote-deploy.sh"
  } else {
    Write-Warn "Deploy script not found, using manual commands..."

    # Manual deployment commands
    $commands = @(
      "docker load -i '/tmp/$TarName'",
      "mkdir -p /opt/ragflowauth/data /opt/ragflowauth/uploads /opt/ragflowauth/ragflow_compose /opt/ragflowauth/backups",
      "docker network ls | grep ragflowauth-network || docker network create ragflowauth-network",
      "docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true",
      "docker rm ragflowauth-backend ragflowauth-frontend 2>/dev/null || true",
      "docker run -d --name ragflowauth-backend --network ragflowauth-network -p 8001:8001 -v /opt/ragflowauth/data:/app/data -v /opt/ragflowauth/uploads:/app/uploads -v /opt/ragflowauth/ragflow_config.json:/app/ragflow_config.json:ro -v /opt/ragflowauth/ragflow_compose:/app/ragflow_compose:ro -v /opt/ragflowauth/backups:/app/data/backups -v /var/run/docker.sock:/var/run/docker.sock ragflowauth-backend:$Tag",
      "docker run -d --name ragflowauth-frontend --network ragflowauth-network -p 3001:80 --link ragflowauth-backend:backend ragflowauth-frontend:$Tag",
      "rm -f '/tmp/$TarName'"
    )

    foreach ($cmd in $commands) {
      Write-Info "Executing: $cmd"
      ssh "${ServerUser}@${ServerHost}" $cmd
    }
  }

  if ($LASTEXITCODE -ne 0) {
    throw "Remote deployment failed"
  }

  Write-Success "Server deployment completed"
} else {
  Write-Step "Skipping server deployment"
}

# ==================== Cleanup ====================
if (-not $SkipCleanup) {
  Write-Step "Cleaning up temporary files"

  $shouldClean = Read-Host "Delete local tar file? (Y/N)"
  if ($shouldClean -eq "Y" -or $shouldClean -eq "y") {
    Remove-Item $TarPath -Force
    Remove-Item $HashPath -Force -ErrorAction SilentlyContinue
    Write-Success "Temporary files deleted"
  } else {
    Write-Info "Keeping temporary files in: $OutPath"
  }

  # Clean up old images on server
  Write-Step "Cleaning up old Docker images on server"

  $cleanupScript = Join-Path $PSScriptRoot "cleanup-images.sh"
  if (Test-Path $cleanupScript) {
    Write-Info "Uploading cleanup script..."
    scp $cleanupScript "${ServerUser}@${ServerHost}:/tmp/cleanup-images.sh"

    Write-Info "Converting line endings..."
    ssh "${ServerUser}@${ServerHost}" "sed -i 's/\r$//' /tmp/cleanup-images.sh"

    Write-Info "Running cleanup script (keeping only current version)..."
    ssh "${ServerUser}@${ServerHost}" "chmod +x /tmp/cleanup-images.sh && /tmp/cleanup-images.sh --keep 1"

    Write-Success "Old images cleaned up on server (only current version kept)"
  } else {
    Write-Warn "Cleanup script not found, skipping image cleanup"
  }
}

# ==================== Complete ====================
Write-Step "Deployment completed!"

Write-Host "`nAccess URLs:" -ForegroundColor Cyan
Write-Host "  Frontend: http://${ServerHost}:3001" -ForegroundColor White
Write-Host "  Backend:  http://${ServerHost}:8001" -ForegroundColor White
Write-Host "`nManagement commands:" -ForegroundColor Cyan
Write-Host "  View containers: ssh ${ServerUser}@${ServerHost} 'docker ps'" -ForegroundColor White
Write-Host "  View logs:      ssh ${ServerUser}@${ServerHost} 'docker logs -f ragflowauth-backend'" -ForegroundColor White
Write-Host "  Restart:        ssh ${ServerUser}@${ServerHost} 'docker restart ragflowauth-backend ragflowauth-frontend'" -ForegroundColor White
