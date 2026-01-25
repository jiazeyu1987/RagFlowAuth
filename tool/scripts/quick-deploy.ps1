#!/usr/bin/env pwsh
# RagflowAuth Quick Deploy Script
# Workflow: Stop containers -> Build images -> Transfer images -> Load images -> Start containers

param(
    [string]$ConfigPath = "tool/scripts/deploy-config.json",
    [string]$Tag = (Get-Date -Format "yyyy-MM-dd-HHmmss"),
    [switch]$SkipBuild,
    [switch]$SkipTransfer,
    [switch]$SkipLoad
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# Load configuration
Write-Host "=== Loading Configuration ===" -ForegroundColor Cyan
$Config = Get-Content "$RepoRoot/$ConfigPath" -Raw | ConvertFrom-Json

$ServerHost = $Config.server.host
$ServerUser = $Config.server.user
$FrontendPort = $Config.docker.frontend_port
$BackendPort = $Config.docker.backend_port
$NetworkName = $Config.docker.network
$DataDir = $Config.paths.data_dir

Write-Host "Server: $ServerUser@$ServerHost"
Write-Host "Tag: $Tag"
Write-Host ""

# Define image names
$FrontendImage = "ragflowauth-frontend:$Tag"
$BackendImage = "ragflowauth-backend:$Tag"

# ========== Step 1: Stop containers on server ==========
if (-not $SkipTransfer) {
    Write-Host "=== Step 1: Stop Server Containers ===" -ForegroundColor Yellow
    ssh "${ServerUser}@${ServerHost}" "docker stop ragflowauth-frontend ragflowauth-backend 2>/dev/null || true"
    Write-Host "Containers stopped" -ForegroundColor Green
    Write-Host ""
}

# ========== Step 2: Build Docker images ==========
if (-not $SkipBuild) {
    Write-Host "=== Step 2: Build Docker Images ===" -ForegroundColor Yellow

    # Build backend image
    Write-Host "Building backend image..." -ForegroundColor Cyan
    Push-Location $RepoRoot
    docker build -f backend/Dockerfile -t $BackendImage .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Backend image build failed!" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location
    Write-Host "Backend image built: $BackendImage" -ForegroundColor Green

    # Build frontend image
    Write-Host "Building frontend image..." -ForegroundColor Cyan
    Push-Location $RepoRoot
    docker build -f fronted/Dockerfile -t $FrontendImage .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Frontend image build failed!" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location
    Write-Host "Frontend image built: $FrontendImage" -ForegroundColor Green
    Write-Host ""
}

# ========== Step 3: Export images ==========
if (-not $SkipTransfer) {
    Write-Host "=== Step 3: Export Images ===" -ForegroundColor Yellow

    $TempDir = "$RepoRoot/tool/scripts/temp"
    New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

    $FrontendTar = "$TempDir/ragflowauth-frontend-$Tag.tar"
    $BackendTar = "$TempDir/ragflowauth-backend-$Tag.tar"

    Write-Host "Exporting frontend image..." -ForegroundColor Cyan
    docker save $FrontendImage -o $FrontendTar
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Frontend image export failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "Frontend image exported: $FrontendTar" -ForegroundColor Green

    Write-Host "Exporting backend image..." -ForegroundColor Cyan
    docker save $BackendImage -o $BackendTar
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Backend image export failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "Backend image exported: $BackendTar" -ForegroundColor Green

    # Calculate checksums
    Write-Host "Calculating checksums..." -ForegroundColor Cyan
    (Get-FileHash $FrontendTar -Algorithm SHA256).Hash | Out-File "$FrontendTar.sha256"
    (Get-FileHash $BackendTar -Algorithm SHA256).Hash | Out-File "$BackendTar.sha256"
    Write-Host "Checksums generated" -ForegroundColor Green
    Write-Host ""
}

# ========== Step 4: Transfer images to server ==========
if (-not $SkipTransfer) {
    Write-Host "=== Step 4: Transfer Images to Server ===" -ForegroundColor Yellow

    Write-Host "Transferring frontend image..." -ForegroundColor Cyan
    scp "$FrontendTar" "${ServerUser}@${ServerHost}:/tmp/"
    scp "$FrontendTar.sha256" "${ServerUser}@${ServerHost}:/tmp/"

    Write-Host "Transferring backend image..." -ForegroundColor Cyan
    scp "$BackendTar" "${ServerUser}@${ServerHost}:/tmp/"
    scp "$BackendTar.sha256" "${ServerUser}@${ServerHost}:/tmp/"

    # Verify checksums
    Write-Host "Verifying checksums..." -ForegroundColor Cyan
    $FrontendTarName = Split-Path $FrontendTar -Leaf
    $BackendTarName = Split-Path $BackendTar -Leaf

    $FrontendHash = ssh "${ServerUser}@${ServerHost}" "sha256sum /tmp/${FrontendTarName} | cut -d' ' -f1"
    $BackendHash = ssh "${ServerUser}@${ServerHost}" "sha256sum /tmp/${BackendTarName} | cut -d' ' -f1"

    $LocalFrontendHash = (Get-Content "$FrontendTar.sha256").Trim()
    $LocalBackendHash = (Get-Content "$BackendTar.sha256").Trim()

    if ($FrontendHash -eq $LocalFrontendHash) {
        Write-Host "Frontend image verified" -ForegroundColor Green
    } else {
        Write-Host "Frontend image checksum failed!" -ForegroundColor Red
        exit 1
    }

    if ($BackendHash -eq $LocalBackendHash) {
        Write-Host "Backend image verified" -ForegroundColor Green
    } else {
        Write-Host "Backend image checksum failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# ========== Step 5: Load images on server ==========
if (-not $SkipLoad) {
    Write-Host "=== Step 5: Load Images on Server ===" -ForegroundColor Yellow

    $FrontendTarName = Split-Path $FrontendTar -Leaf
    $BackendTarName = Split-Path $BackendTar -Leaf

    Write-Host "Loading frontend image..." -ForegroundColor Cyan
    ssh "${ServerUser}@${ServerHost}" "docker load -i /tmp/${FrontendTarName}"

    Write-Host "Loading backend image..." -ForegroundColor Cyan
    ssh "${ServerUser}@${ServerHost}" "docker load -i /tmp/${BackendTarName}"

    Write-Host "Cleaning temporary files..." -ForegroundColor Cyan
    ssh "${ServerUser}@${ServerHost}" "rm -f /tmp/${FrontendTarName} /tmp/${FrontendTarName}.sha256 /tmp/${BackendTarName} /tmp/${BackendTarName}.sha256"

    Write-Host "Images loaded" -ForegroundColor Green
    Write-Host ""
}

# ========== Step 6: Start containers ==========
Write-Host "=== Step 6: Start Containers ===" -ForegroundColor Yellow

# Get existing container configuration
Write-Host "Getting existing container configuration..." -ForegroundColor Cyan

$FrontendVolumes = ssh "${ServerUser}@${ServerHost}" "docker inspect ragflowauth-frontend --format '{{range .Mounts}}{{.Source}}:{{.Destination}}{{\" \"}}{{end}}' 2>/dev/null || echo ''"
$BackendVolumes = ssh "${ServerUser}@${ServerHost}" "docker inspect ragflowauth-backend --format '{{range .Mounts}}{{.Source}}:{{.Destination}}{{\" \"}}{{end}}' 2>/dev/null || echo ''"

$FrontendEnv = ssh "${ServerUser}@${ServerHost}" "docker inspect ragflowauth-frontend --format '{{range .Config.Env}}{{.}} {{end}}' 2>/dev/null || echo ''"
$BackendEnv = ssh "${ServerUser}@${ServerHost}" "docker inspect ragflowauth-backend --format '{{range .Config.Env}}{{.}} {{end}}' 2>/dev/null || echo ''"

# Force stop and remove existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Cyan
ssh "${ServerUser}@${ServerHost}" "docker stop ragflowauth-frontend ragflowauth-backend 2>/dev/null || true"

Write-Host "Removing existing containers..." -ForegroundColor Cyan
ssh "${ServerUser}@${ServerHost}" "docker rm -f ragflowauth-frontend ragflowauth-backend 2>/dev/null || true"

# Start frontend container
Write-Host "Starting frontend container..." -ForegroundColor Cyan
$FrontendCmd = "docker run -d --name ragflowauth-frontend"
$FrontendCmd += " --network $NetworkName"
$FrontendCmd += " -p ${FrontendPort}:80"
$FrontendCmd += " --restart unless-stopped"

if ($FrontendVolumes) {
    $Volumes = $FrontendVolumes.Trim().Split(' ') | Where-Object { $_ -ne '' }
    foreach ($v in $Volumes) {
        $FrontendCmd += " -v $v"
    }
}

ssh "${ServerUser}@${ServerHost}" "$FrontendCmd $FrontendImage"
Write-Host "Frontend container started: $FrontendImage" -ForegroundColor Green

# Start backend container
Write-Host "Starting backend container..." -ForegroundColor Cyan
$BackendCmd = "docker run -d --name ragflowauth-backend"
$BackendCmd += " --network $NetworkName"
$BackendCmd += " -p ${BackendPort}:${BackendPort}"
$BackendCmd += " -v ${DataDir}/data:/app/data"
$BackendCmd += " -v ${DataDir}/uploads:/app/uploads"
$BackendCmd += " -v ${DataDir}/ragflow_config.json:/app/ragflow_config.json:ro"
$BackendCmd += " --restart unless-stopped"

if ($BackendVolumes) {
    $Volumes = $BackendVolumes.Trim().Split(' ') | Where-Object { $_ -ne '' }
    foreach ($v in $Volumes) {
        if (-not $v.Contains('/app/data') -and -not $v.Contains('/app/uploads') -and -not $v.Contains('ragflow_config.json')) {
            $BackendCmd += " -v $v"
        }
    }
}

ssh "${ServerUser}@${ServerHost}" "$BackendCmd $BackendImage"
Write-Host "Backend container started: $BackendImage" -ForegroundColor Green
Write-Host ""

# ========== Step 7: Verify deployment ==========
Write-Host "=== Step 7: Verify Deployment ===" -ForegroundColor Yellow

Start-Sleep -Seconds 3

$FrontendStatus = ssh "${ServerUser}@${ServerHost}" "docker inspect ragflowauth-frontend --format '{{.State.Status}}' 2>/dev/null || echo 'not running'"
$BackendStatus = ssh "${ServerUser}@${ServerHost}" "docker inspect ragflowauth-backend --format '{{.State.Status}}' 2>/dev/null || echo 'not running'"

Write-Host "Frontend status: $FrontendStatus" -ForegroundColor $(if ($FrontendStatus -eq "running") { "Green" } else { "Red" })
Write-Host "Backend status: $BackendStatus" -ForegroundColor $(if ($BackendStatus -eq "running") { "Green" } else { "Red" })

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "Frontend URL: http://${ServerHost}:${FrontendPort}"
Write-Host "Backend URL: http://${ServerHost}:${BackendPort}"

# Clean up local temporary files
if (Test-Path $TempDir) {
    Remove-Item -Recurse -Force $TempDir
    Write-Host "Cleaned local temporary files" -ForegroundColor Cyan
}
