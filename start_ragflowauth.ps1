$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPort = 8001
$frontendPort = 3000
$openUrl = 'http://127.0.0.1:3000/chat'
$backendHealthUrl = 'http://127.0.0.1:8001/health'
$frontendHealthUrl = 'http://127.0.0.1:3000'

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

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return $true
            }
        } catch {
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Wait-PortReady {
    param(
        [int]$Port,
        [int]$TimeoutSeconds
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ((Get-PortPids -Port $Port).Count -gt 0) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
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

Stop-PortProcesses -Port $backendPort
Start-Sleep -Seconds 1

$backendCmd = "cd /d `"$root`" && python -m backend"
$frontendCmd = "cd /d `"$root\fronted`" && set BROWSER=none && npm start"

Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', $backendCmd -WindowStyle Normal | Out-Null

$frontendRunning = (Get-PortPids -Port $frontendPort).Count -gt 0
if (-not $frontendRunning) {
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', $frontendCmd -WindowStyle Normal | Out-Null
}

$backendReady = Wait-HttpReady -Url $backendHealthUrl -TimeoutSeconds 90
$frontendReady = Wait-HttpReady -Url $frontendHealthUrl -TimeoutSeconds 120

if (-not $backendReady) {
    throw "Backend failed to become ready on $backendHealthUrl"
}

if (-not $frontendReady) {
    throw "Frontend failed to become ready on $frontendHealthUrl"
}

Open-Url -Url $openUrl
