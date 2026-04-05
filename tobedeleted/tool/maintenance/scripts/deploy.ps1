# RagflowAuth Deployment Tool
# Purpose: Build, package, transfer and deploy Docker images to remote server

param(
  [Parameter(Mandatory = $false)]
  [string]$Tag = "",  # Empty by default, will use version from .version file

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
  [string]$OutDir = "dist",

  # Version increment options
  [Parameter(Mandatory = $false)]
  [switch]$IncrementPatch = $false,  # 1.0.0 -> 1.0.1

  [Parameter(Mandatory = $false)]
  [switch]$IncrementMinor = $false,  # 1.0.0 -> 1.1.0

  [Parameter(Mandatory = $false)]
  [switch]$IncrementMajor = $false,  # 1.0.0 -> 2.0.0

  [Parameter(Mandatory = $false)]
  [switch]$NoAutoIncrement = $false  # Don't auto-increment version
)

$ErrorActionPreference = "Stop"

# ==================== Version Management Functions ====================

function Get-CurrentVersion {
  param([string]$RepoRoot)

  $versionFile = Join-Path $RepoRoot ".version"

  if (Test-Path $versionFile) {
    $version = Get-Content $versionFile -Raw
    return $version.Trim()
  } else {
    return "1.0.0"
  }
}

function Set-CurrentVersion {
  param(
    [string]$RepoRoot,
    [string]$Version
  )

  $versionFile = Join-Path $RepoRoot ".version"
  $Version | Set-Content -Encoding ASCII -NoNewline -Path $versionFile
}

function Increment-Version {
  param(
    [string]$Version,
    [switch]$Major,
    [switch]$Minor,
    [switch]$Patch
  )

  $parts = $Version -split '\.'
  $major = [int]$parts[0]
  $minor = [int]$parts[1]
  $patch = [int]$parts[2]

  if ($Major) {
    $major++
    $minor = 0
    $patch = 0
  } elseif ($Minor) {
    $minor++
    $patch = 0
  } elseif ($Patch) {
    $patch++
  } else {
    # Default: increment patch
    $patch++
  }

  return "$major.$minor.$patch"
}

# ==================== Output Functions ====================
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
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$ComposeFilePath = Join-Path $RepoRoot $ComposeFile
$OutPath = Join-Path $RepoRoot $OutDir

# ==================== Version Management ====================
if ([string]::IsNullOrWhiteSpace($Tag)) {
  # No Tag specified, use version from .version file
  $currentVersion = Get-CurrentVersion -RepoRoot $RepoRoot

  if ($IncrementMajor -or $IncrementMinor -or $IncrementPatch) {
    # Increment version
    $newVersion = Increment-Version -Version $currentVersion -Major:$IncrementMajor -Minor:$IncrementMinor -Patch:$IncrementPatch
    Write-Step "Version bump: $currentVersion -> $newVersion"
    Set-CurrentVersion -RepoRoot $RepoRoot -Version $newVersion
    $Tag = $newVersion
  } elseif (-not $NoAutoIncrement) {
    # Auto-increment patch version by default
    $newVersion = Increment-Version -Version $currentVersion -Patch
    Write-Step "Version bump: $currentVersion -> $newVersion"
    Set-CurrentVersion -RepoRoot $RepoRoot -Version $newVersion
    $Tag = $newVersion
  } else {
    # Use current version without incrementing
    $Tag = $currentVersion
    Write-Step "Using version: $Tag (no increment)"
  }
} else {
  # Tag explicitly provided, use it
  Write-Step "Using explicit tag: $Tag"
}

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
  # ⚠️ CRITICAL WARNING
  Write-Warn "============================================"
  Write-Warn "⚠️  WARNING: 跳过镜像构建 (-SkipBuild)"
  Write-Warn "============================================"
  Write-Warn "如果您修改了代码，服务器将运行旧版本！"
  Write-Warn ""
  Write-Warn "仅在以下情况使用 -SkipBuild："
  Write-Warn "  1. 只修改了配置文件（没有代码修改）"
  Write-Warn "  2. 只修改了前端 HTML/CSS"
  Write-Warn "  3. 完全确认镜像已是最新的"
  Write-Warn ""
  Write-Warn "如果修改了 Python/JS 代码，请按 Ctrl+C 取消，然后："
  Write-Warn "  1. 不使用 -SkipBuild 参数"
  Write-Warn "  2. 完整运行部署流程"
  Write-Warn ""

  # Auto-confirm in scripts, but show warning
  Write-Info "Continuing with -SkipBuild..."
  Start-Sleep -Seconds 3
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

function Resolve-RemoteStagingDir {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Host,

    [Parameter(Mandatory = $true)]
    [string]$User
  )

  # Pick a writable dir with the most free space.
  # Prefer non-root partitions first to avoid filling / (common cause of scp failures to /tmp).
  $pickCmd = 'bash -lc ''set -e; candidates="/var/lib/docker/tmp /mnt/replica/_tmp /home/root/_tmp /tmp"; best=""; best_avail=-1; for d in $candidates; do mkdir -p "$d" 2>/dev/null || true; t="$d/.ragflowauth_write_test_$$"; (touch "$t" 2>/dev/null && rm -f "$t") || continue; avail=$(df -Pk "$d" 2>/dev/null | tail -n 1 | awk "{print \$4}"); [ -n "$avail" ] || continue; if [ "$avail" -gt "$best_avail" ]; then best="$d"; best_avail="$avail"; fi; done; echo "$best"'''
  $out = ssh "${User}@${Host}" $pickCmd 2>$null
  $dir = ($out | Select-Object -Last 1).Trim()
  if (-not $dir) {
    return "/tmp"
  }
  return $dir
}

# ==================== Step 3: Transfer to Server ====================
if (-not $SkipTransfer) {
  Write-Step "Step 3/4: Transferring images to server"

  Write-Info "Target server: ${ServerUser}@${ServerHost}"
  Write-Info "Transferring file: $TarName"

  $RemoteStagingDir = Resolve-RemoteStagingDir -Host $ServerHost -User $ServerUser
  Write-Info "Remote staging dir: $RemoteStagingDir"
  ssh "${ServerUser}@${ServerHost}" "mkdir -p '$RemoteStagingDir'"
  $RemoteTarPath = "${RemoteStagingDir}/$TarName"
  scp $TarPath "${ServerUser}@${ServerHost}:$RemoteTarPath"

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
  if (-not (Test-Path $localDeployScript)) {
    $localDeployScript = Join-Path $RepoRoot "tool/scripts/remote-deploy.sh"
  }

  if (Test-Path $localDeployScript) {
    Write-Info "Uploading deploy script..."
    scp $localDeployScript "${ServerUser}@${ServerHost}:/tmp/remote-deploy.sh"

    Write-Info "Converting line endings..."
    ssh "${ServerUser}@${ServerHost}" "sed -i 's/\r$//' /tmp/remote-deploy.sh"

    Write-Info "Executing remote deploy script..."
    $remoteTar = if ($RemoteTarPath) { $RemoteTarPath } else { "/tmp/$TarName" }
    ssh "${ServerUser}@${ServerHost}" "chmod +x /tmp/remote-deploy.sh && TAG=$Tag TAR_FILE='$remoteTar' SKIP_CONFIG_CREATE=1 /tmp/remote-deploy.sh --tag '$Tag' --tar-file '$remoteTar'"
  } else {
    Write-Warn "Deploy script not found, using manual commands..."

    # Manual deployment commands
    $remoteTar = if ($RemoteTarPath) { $RemoteTarPath } else { "/tmp/$TarName" }
    $commands = @(
      "docker load -i '$remoteTar'",
      "mkdir -p /opt/ragflowauth/data /opt/ragflowauth/uploads /opt/ragflowauth/ragflow_compose /opt/ragflowauth/backups",
      "docker network ls | grep ragflowauth-network || docker network create ragflowauth-network",
      "docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true",
      "docker rm ragflowauth-backend ragflowauth-frontend 2>/dev/null || true",
      "docker run -d --name ragflowauth-backend --network ragflowauth-network -p 8001:8001 -v /opt/ragflowauth/data:/app/data -v /opt/ragflowauth/uploads:/app/uploads -v /opt/ragflowauth/ragflow_config.json:/app/ragflow_config.json:ro -v /opt/ragflowauth/ragflow_compose:/app/ragflow_compose:ro -v /opt/ragflowauth/backups:/app/data/backups -v /var/run/docker.sock:/var/run/docker.sock ragflowauth-backend:$Tag",
      "docker run -d --name ragflowauth-frontend --network ragflowauth-network -p 3001:80 --link ragflowauth-backend:backend ragflowauth-frontend:$Tag",
      "rm -f '$remoteTar'"
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

  Remove-Item $TarPath -Force -ErrorAction SilentlyContinue
  Remove-Item $HashPath -Force -ErrorAction SilentlyContinue
  Write-Success "Temporary files deleted"

  if ($RemoteTarPath) {
    Write-Info "Cleaning remote tar: $RemoteTarPath"
    ssh "${ServerUser}@${ServerHost}" "rm -f '$RemoteTarPath' 2>/dev/null || true"
  }

  # Clean up old images on server
  Write-Step "Cleaning up old Docker images on server"

  $cleanupScript = Join-Path $PSScriptRoot "cleanup-images.sh"
  if (Test-Path $cleanupScript) {
    Write-Info "Uploading cleanup script..."
    scp $cleanupScript "${ServerUser}@${ServerHost}:/tmp/cleanup-images.sh" 2>$null

    Write-Info "Converting line endings..."
    ssh "${ServerUser}@${ServerHost}" "sed -i 's/\r$//' /tmp/cleanup-images.sh" 2>$null

    Write-Info "Running cleanup script (keeping only running images)..."
    ssh "${ServerUser}@${ServerHost}" "chmod +x /tmp/cleanup-images.sh && yes | /tmp/cleanup-images.sh" 2>$null

    Write-Success "Old images cleaned up on server (only running images kept)"
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
