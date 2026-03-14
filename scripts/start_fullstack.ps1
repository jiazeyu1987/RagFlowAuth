param(
  [string]$Url = "http://localhost:3000",
  [int]$BackendPort = 8001,
  [int]$FrontendPort = 3000,
  [int]$BackendTimeoutSec = 120,
  [int]$FrontendTimeoutSec = 240
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendDir = Join-Path $repoRoot "fronted"
$lockDir = Join-Path $repoRoot "tmp"
$lockPath = Join-Path $lockDir "start_fullstack.lock"
New-Item -Path $lockDir -ItemType Directory -Force | Out-Null
try {
  $lockHandle = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
} catch {
  exit 0
}

function Get-ListeningPids {
  param([int]$Port)
  $pids = @()
  try {
    $items = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
    if ($items) {
      $pids += ($items | Select-Object -ExpandProperty OwningProcess -Unique)
    }
  } catch {
  }
  if (@($pids).Count -eq 0) {
    try {
      $lines = netstat -ano | Select-String -Pattern "LISTENING"
      foreach ($line in $lines) {
        $parts = ($line.ToString() -split "\s+") | Where-Object { $_ -ne "" }
        if (@($parts).Count -lt 5) { continue }
        $local = $parts[1]
        $pidText = $parts[-1]
        if ($local -match ":(\d+)$") {
          $p = [int]$Matches[1]
          if ($p -eq $Port) {
            $pidVal = 0
            if ([int]::TryParse($pidText, [ref]$pidVal)) {
              $pids += $pidVal
            }
          }
        }
      }
    } catch {
    }
  }
  return ,@($pids | Sort-Object -Unique)
}

function Stop-PortListeners {
  param([int]$Port)
  $pids = Get-ListeningPids -Port $Port
  foreach ($procId in $pids) {
    try {
      Stop-Process -Id $procId -Force -ErrorAction Stop
    } catch {
    }
  }
  if (@($pids).Count -gt 0) {
    Start-Sleep -Seconds 1
  }
}

function Wait-HttpReady {
  param(
    [string]$TargetUrl,
    [int]$TimeoutSec
  )
  $started = Get-Date
  while (((Get-Date) - $started).TotalSeconds -lt $TimeoutSec) {
    try {
      $resp = Invoke-WebRequest -Uri $TargetUrl -TimeoutSec 3 -UseBasicParsing
      if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
        return $true
      }
    } catch {
    }
    Start-Sleep -Seconds 1
  }
  return $false
}

if (-not (Test-Path $frontendDir)) {
  throw "fronted directory not found: $frontendDir"
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "python not found in PATH"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm not found in PATH"
}

try {
  $backendRunning = @((Get-ListeningPids -Port $BackendPort)).Count -gt 0
  if ($backendRunning) {
    Write-Host "Backend detected on port $BackendPort, restarting..."
  } else {
    Write-Host "Backend not running on port $BackendPort, starting..."
  }
  Stop-PortListeners -Port $BackendPort

  $backendCmd = "Set-Location -LiteralPath '$repoRoot'; python -m backend"
  Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCmd | Out-Null

  $frontendRunning = @((Get-ListeningPids -Port $FrontendPort)).Count -gt 0
  if ($frontendRunning) {
    Write-Host "Frontend already running on port $FrontendPort, reusing..."
  } else {
    Write-Host "Frontend not running on port $FrontendPort, starting..."
    $frontendCmd = "cd /d `"$frontendDir`" && set BROWSER=none&&npm start"
    Start-Process -FilePath "cmd.exe" -WindowStyle Hidden -ArgumentList "/c", $frontendCmd | Out-Null
  }

  Write-Host "Waiting for backend..."
  if (-not (Wait-HttpReady -TargetUrl "http://localhost:$BackendPort/health" -TimeoutSec $BackendTimeoutSec)) {
    throw "backend failed to become ready on http://localhost:$BackendPort/health"
  }

  Write-Host "Waiting for frontend..."
  if (-not (Wait-HttpReady -TargetUrl "http://localhost:$FrontendPort" -TimeoutSec $FrontendTimeoutSec)) {
    throw "frontend failed to become ready on http://localhost:$FrontendPort"
  }

  Write-Host "Opening $Url"
  Start-Process $Url | Out-Null
  Write-Host "Done."
} finally {
  try {
    if ($null -ne $lockHandle) {
      $lockHandle.Close()
      $lockHandle.Dispose()
    }
  } catch {
  }
}
