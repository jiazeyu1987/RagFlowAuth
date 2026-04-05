#!/usr/bin/env pwsh
# 大文件上传脚本（支持断点续传）
# 用途：当 tool.py 的还原功能因网络问题失败时使用

param(
    [Parameter(Mandatory = $true)]
    [string]$LocalFile,

    [Parameter(Mandatory = $false)]
    [string]$RemotePath = "/var/lib/docker/tmp/images.tar",

    [Parameter(Mandatory = $false)]
    [string]$ServerHost = "172.30.30.57",

    [Parameter(Mandatory = $false)]
    [string]$ServerUser = "root"
)

$ErrorActionPreference = "Stop"

Write-Host "=== 大文件上传工具 ===" -ForegroundColor Cyan
Write-Host ""

# 检查文件是否存在
if (-not (Test-Path $LocalFile)) {
    Write-Host "错误: 文件不存在: $LocalFile" -ForegroundColor Red
    exit 1
}

$FileSize = (Get-Item $LocalFile).Length / 1MB
Write-Host "本地文件: $LocalFile" -ForegroundColor White
Write-Host "文件大小: $([math]::Round($FileSize, 2)) MB" -ForegroundColor White
Write-Host "目标服务器: ${ServerUser}@${ServerHost}:${RemotePath}" -ForegroundColor White
Write-Host ""

# 确保远程目录存在
Write-Host "创建远程目录..." -ForegroundColor Cyan
$RemoteDir = Split-Path $RemotePath -Parent
ssh "${ServerUser}@${ServerHost}" "mkdir -p $RemoteDir"

Write-Host "开始上传..." -ForegroundColor Cyan
Write-Host ""

$StartTime = Get-Date
$Success = $false
$MaxRetries = 5

for ($i = 1; $i -le $MaxRetries; $i++) {
    try {
        Write-Host "尝试 $i/$MaxRetries..." -ForegroundColor Yellow

        # 使用 rsync（支持断点续传）
        $Result = Invoke-Expression "rsync -avz --progress -e 'ssh -o BatchMode=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3' '$LocalFile' '${ServerUser}@${ServerHost}:${RemotePath}'" 2>&1

        if ($LASTEXITCODE -eq 0) {
            $Success = $true
            break
        } else {
            Write-Host "失败: $Result" -ForegroundColor Red
            if ($i -lt $MaxRetries) {
                Write-Host "等待 5 秒后重试..." -ForegroundColor Yellow
                Start-Sleep -Seconds 5
            }
        }
    } catch {
        Write-Host "异常: $_" -ForegroundColor Red
        if ($i -lt $MaxRetries) {
            Write-Host "等待 5 秒后重试..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }
}

$ElapsedTime = (Get-Date) - $StartTime
$Speed = $FileSize / $ElapsedTime.TotalSeconds

Write-Host ""
if ($Success) {
    Write-Host "✅ 上传成功！" -ForegroundColor Green
    Write-Host "耗时: $([math]::Round($ElapsedTime.TotalSeconds, 1)) 秒" -ForegroundColor White
    Write-Host "速度: $([math]::Round($Speed, 2)) MB/s" -ForegroundColor White

    # 验证文件
    Write-Host ""
    Write-Host "验证远程文件..." -ForegroundColor Cyan
    $RemoteSize = ssh "${ServerUser}@${ServerHost}" "stat -f%z $RemotePath 2>/dev/null || stat -c%s $RemotePath 2>/dev/null"
    $LocalSizeBytes = (Get-Item $LocalFile).Length

    if ($RemoteSize -eq $LocalSizeBytes) {
        Write-Host "✅ 文件验证成功（大小匹配）" -ForegroundColor Green
    } else {
        Write-Host "⚠️  文件大小不匹配！" -ForegroundColor Yellow
        Write-Host "  本地: $LocalSizeBytes 字节" -ForegroundColor White
        Write-Host "  远程: $RemoteSize 字节" -ForegroundColor White
    }
} else {
    Write-Host "❌ 上传失败（重试 $MaxRetries 次后仍失败）" -ForegroundColor Red
    Write-Host ""
    Write-Host "建议:" -ForegroundColor Yellow
    Write-Host "1. 检查网络连接" -ForegroundColor White
    Write-Host "2. 检查服务器磁盘空间: ssh ${ServerUser}@${ServerHost} 'df -h'" -ForegroundColor White
    Write-Host "3. 尝试分卷上传" -ForegroundColor White
    exit 1
}
