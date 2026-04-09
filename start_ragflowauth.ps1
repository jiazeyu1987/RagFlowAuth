$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPort = 8001
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

Stop-PortProcesses -Port $backendPort
Start-Sleep -Seconds 1

$backendCmd = "cd /d `"$root`" && python -m backend"
$frontendCmd = "cd /d `"$root\fronted`" && set BROWSER=none && npm start"

Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', $backendCmd -WindowStyle Normal | Out-Null

$frontendRunning = (Get-PortPids -Port $frontendPort).Count -gt 0
if (-not $frontendRunning) {
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', $frontendCmd -WindowStyle Normal | Out-Null
}

Open-Url -Url $openUrl
