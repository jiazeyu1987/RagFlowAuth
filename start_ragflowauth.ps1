$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPort = 8001
$backendHost = '0.0.0.0'
$frontendPort = 3001
$openUrl = 'http://127.0.0.1:3001/chat'

function Get-PortPids {
    param([int]$Port)
    $lines = netstat -ano -p tcp | Select-String ":$Port "
    $portPids = @()
    foreach ($line in $lines) {
        $parts = ($line.ToString() -replace '\s+', ' ').Trim().Split(' ')
        if ($parts.Length -ge 5 -and $parts[3] -eq 'LISTENING') {
            $listeningPid = 0
            if ([int]::TryParse($parts[4], [ref]$listeningPid)) {
                $portPids += $listeningPid
            }
        }
    }
    $portPids | Sort-Object -Unique
}

function Stop-PortProcesses {
    param([int]$Port)
    $portPids = Get-PortPids -Port $Port
    foreach ($processId in $portPids) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
        } catch {
        }
    }
}

function Open-Url {
    param([string]$Url)
    try {
        & cmd.exe /c start "" "$Url"
        return
    } catch {
    }
    try {
        Start-Process -FilePath 'rundll32.exe' -ArgumentList 'url.dll,FileProtocolHandler', $Url | Out-Null
        return
    } catch {
    }
    Start-Process -FilePath 'explorer.exe' -ArgumentList $Url | Out-Null
}

function Get-JwtSecretValue {
    $envSecret = [string]$env:JWT_SECRET_KEY
    if (-not [string]::IsNullOrWhiteSpace($envSecret)) {
        return $envSecret.Trim()
    }

    $envFilePath = Join-Path $root '.env'
    if (-not (Test-Path -LiteralPath $envFilePath)) {
        return $null
    }

    foreach ($line in Get-Content -LiteralPath $envFilePath) {
        if ($line -match '^\s*JWT_SECRET_KEY=(.*)$') {
            return $matches[1].Trim()
        }
    }

    return $null
}

function Assert-BackendJwtSecret {
    $jwtSecret = Get-JwtSecretValue
    if ([string]::IsNullOrWhiteSpace($jwtSecret)) {
        throw 'Missing JWT_SECRET_KEY. Set it in the current shell or in .env before starting backend.'
    }
    if ($jwtSecret -eq 'your-secret-key-change-in-production') {
        throw 'JWT_SECRET_KEY is still using the default insecure value. Update it before starting backend.'
    }
}

Assert-BackendJwtSecret

Stop-PortProcesses -Port $backendPort
Start-Sleep -Seconds 1

$backendCmd = "cd /d `"$root`" && python -m backend run --host $backendHost --port $backendPort"
$frontendCmd = "cd /d `"$root\fronted`" && set BROWSER=none && npm start"

Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', $backendCmd -WindowStyle Normal | Out-Null

$frontendRunning = (Get-PortPids -Port $frontendPort).Count -gt 0
if (-not $frontendRunning) {
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', $frontendCmd -WindowStyle Normal | Out-Null
}

Open-Url -Url $openUrl
