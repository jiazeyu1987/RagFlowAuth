# Enable-WindowsShare.ps1
# 自动开启Windows文件共享并创建D:\datas共享

Write-Host "正在配置Windows文件共享..." -ForegroundColor Green

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "错误: 需要管理员权限！请右键点击此脚本，选择'以管理员身份运行'" -ForegroundColor Red
    pause
    exit 1
}

# 1. 创建 D:\datas 目录（如果不存在）
$datasPath = "D:\datas"
if (-not (Test-Path $datasPath)) {
    Write-Host "创建目录: $datasPath" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $datasPath -Force | Out-Null
} else {
    Write-Host "目录已存在: $datasPath" -ForegroundColor Green
}

# 2. 开启文件共享防火墙规则
Write-Host "开启防火墙文件共享规则..." -ForegroundColor Yellow
try {
    # 开启SMB相关的防火墙规则
    netsh advfirewall firewall set rule group="File and Printer Sharing" new enable=Yes | Out-Null
    Write-Host "✓ 文件共享防火墙规则已开启" -ForegroundColor Green
} catch {
    Write-Host "警告: 无法自动开启防火墙规则，请手动检查" -ForegroundColor Yellow
}

# 3. 创建SMB共享
Write-Host "创建SMB共享..." -ForegroundColor Yellow
try {
    # 检查共享是否已存在
    $existingShare = Get-SmbShare -Name "datas" -ErrorAction SilentlyContinue
    if ($existingShare) {
        Write-Host "共享 'datas' 已存在，删除重建..." -ForegroundColor Yellow
        Remove-SmbShare -Name "datas" -Force
    }

    # 创建新共享
    New-SmbShare -Name "datas" -Path $datasPath -FullAccess "BJB110", "Administrator" -ReadAccess "Everyone" -ErrorAction Stop
    Write-Host "✓ SMB共享创建成功: \\你的电脑IP\datas" -ForegroundColor Green
} catch {
    Write-Host "错误: 无法创建SMB共享" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    pause
    exit 1
}

# 4. 设置文件夹权限（给当前用户完全控制）
Write-Host "设置文件夹权限..." -ForegroundColor Yellow
try {
    $acl = Get-Acl $datasPath
    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "BJB110",
        "FullControl",
        "ContainerInherit,ObjectInherit",
        "None",
        "Allow"
    )
    $acl.SetAccessRule($accessRule)
    Set-Acl $datasPath $acl
    Write-Host "✓ 文件夹权限设置成功" -ForegroundColor Green
} catch {
    Write-Host "警告: 无法设置文件夹权限" -ForegroundColor Yellow
}

# 5. 显示配置信息
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "配置完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "共享名称: datas" -ForegroundColor White
Write-Host "本地路径: D:\datas" -ForegroundColor White
Write-Host "网络路径: \\192.168.112.72\datas" -ForegroundColor White
Write-Host "用户名: BJB110" -ForegroundColor White
Write-Host "`n接下来，脚本将自动连接服务器并完成配置..." -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

Start-Sleep -Seconds 3
