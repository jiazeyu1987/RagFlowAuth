# Portainer 诊断脚本
# 用于检查远程服务器上的 Portainer 状态

param(
    [string]$ServerIP = "172.30.30.58",
    [string]$User = "root"
)

$ErrorActionPreference = "Continue"

Write-Host "==================== Portainer 状态检查 ====================" -ForegroundColor Cyan
Write-Host "服务器: $User@$ServerIP"
Write-Host ""

function Run-SSH {
    param([string]$Command)
    $result = ssh "$User@${ServerIP}" $Command 2>&1
    return $result
}

# 1. 检查 Portainer 容器状态
Write-Host "[1/7] 检查 Portainer 容器状态..." -ForegroundColor Yellow
$output = Run-SSH "docker ps -a --filter 'name=portainer' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
Write-Host $output
Write-Host ""

# 2. 检查容器是否在运行
Write-Host "[2/7] 检查容器运行状态..." -ForegroundColor Yellow
$isRunning = Run-SSH "docker ps --filter 'name=portainer' --format '{{.Names}}' | wc -l"
if ($isRunning -eq 0) {
    Write-Host "⚠️  Portainer 容器未运行！" -ForegroundColor Red
    Write-Host "修复命令: docker start portainer" -ForegroundColor Yellow
} else {
    Write-Host "✓ Portainer 容器正在运行" -ForegroundColor Green
}
Write-Host ""

# 3. 检查 Portainer 日志
Write-Host "[3/7] 检查 Portainer 日志（最近20行）..." -ForegroundColor Yellow
$output = Run-SSH "docker logs portainer --tail 20 2>&1"
Write-Host $output
Write-Host ""

# 4. 检查端口监听
Write-Host "[4/7] 检查端口 9000 监听状态..." -ForegroundColor Yellow
$output = Run-SSH "netstat -tlnp 2>/dev/null | grep :9000 || ss -tlnp | grep :9000"
if ($output) {
    Write-Host "✓ 端口 9000 正在监听:" -ForegroundColor Green
    Write-Host $output
} else {
    Write-Host "⚠️  端口 9000 未监听！" -ForegroundColor Red
}
Write-Host ""

# 5. 检查防火墙
Write-Host "[5/7] 检查防火墙规则..." -ForegroundColor Yellow
$firewall = Run-SSH "firewall-cmd --list-ports 2>/dev/null"
if ($firewall -match "9000/tcp") {
    Write-Host "✓ 防火墙已允许端口 9000" -ForegroundColor Green
} else {
    Write-Host "⚠️  防火墙可能未开放端口 9000" -ForegroundColor Red
    Write-Host "修复命令: firewall-cmd --add-port=9000/tcp --permanent && firewall-cmd --reload" -ForegroundColor Yellow
}
Write-Host ""

# 6. 测试本地访问
Write-Host "[6/7] 测试本地访问 Portainer..." -ForegroundColor Yellow
$output = Run-SSH "curl -I -s -m 5 http://localhost:9000 2>&1 | head -5"
if ($output -match "HTTP") {
    Write-Host "✓ Portainer Web 服务响应正常" -ForegroundColor Green
    Write-Host $output
} else {
    Write-Host "⚠️  Portainer Web 服务无响应" -ForegroundColor Red
    Write-Host $output
}
Write-Host ""

# 7. 检查 Docker 卷
Write-Host "[7/7] 检查 Portainer 数据卷..." -ForegroundColor Yellow
$output = Run-SSH "docker volume ls | grep portainer"
Write-Host $output
Write-Host ""

Write-Host "==================== 诊断完成 ====================" -ForegroundColor Cyan
Write-Host ""

# 提供修复建议
Write-Host "常见问题和修复方法:" -ForegroundColor Yellow
Write-Host ""

Write-Host "1. Portainer 容器未运行:" -ForegroundColor White
Write-Host "   ssh root@${ServerIP} 'docker start portainer'"
Write-Host ""

Write-Host "2. Portainer 容器不存在（需要重新创建）:" -ForegroundColor White
Write-Host "   ssh root@${ServerIP} 'docker run -d -p 9000:9000 --name portainer --restart=unless-stopped -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer'"
Write-Host ""

Write-Host "3. 防火墙阻止访问:" -ForegroundColor White
Write-Host "   ssh root@${ServerIP} 'firewall-cmd --add-port=9000/tcp --permanent && firewall-cmd --reload'"
Write-Host ""

Write-Host "4. 查看详细日志:" -ForegroundColor White
Write-Host "   ssh root@${ServerIP} 'docker logs -f portainer'"
Write-Host ""
