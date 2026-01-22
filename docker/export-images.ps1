param(
  [Parameter(Mandatory = $false)]
  [string]$Tag = "local",

  [Parameter(Mandatory = $false)]
  [string]$OutDir = "dist"
)

$ErrorActionPreference = "Stop"

function Ensure-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing required command: $Name"
  }
}

Ensure-Command docker

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ComposeFile = Join-Path $RepoRoot "docker\\docker-compose.yml"
if (-not (Test-Path $ComposeFile)) {
  throw "Not found: $ComposeFile"
}

$OutPath = Join-Path $RepoRoot $OutDir
New-Item -ItemType Directory -Force -Path $OutPath | Out-Null

Write-Host "Building images (tag=$Tag)..."
$env:RAGFLOWAUTH_TAG = $Tag
docker compose -f $ComposeFile build

Write-Host "Resolving image list..."
$images = (docker compose -f $ComposeFile config --images) | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() }
if (-not $images -or $images.Count -lt 2) {
  throw "Failed to resolve images via 'docker compose config --images'. Got: $($images -join ', ')"
}

$TarPath = Join-Path $OutPath ("ragflowauth-images_{0}.tar" -f $Tag)

Write-Host "Exporting to: $TarPath"
& docker save -o $TarPath $images

$Hash = Get-FileHash -Algorithm SHA256 -Path $TarPath
$HashPath = "$TarPath.sha256"
("$($Hash.Hash)  $(Split-Path -Leaf $TarPath)") | Set-Content -Encoding ASCII -NoNewline -Path $HashPath

Write-Host ""
Write-Host "Done."
Write-Host "Images:"
$images | ForEach-Object { Write-Host "  - $_" }
Write-Host ""
Write-Host "Deliverables:"
Write-Host "  - $TarPath"
Write-Host "  - $HashPath"
Write-Host ""
Write-Host "On the target machine:"
Write-Host "  docker load -i $(Split-Path -Leaf $TarPath)"
Write-Host "  `$env:RAGFLOWAUTH_TAG='$Tag'"
Write-Host "  docker compose -f docker/docker-compose.prebuilt.yml up -d"
