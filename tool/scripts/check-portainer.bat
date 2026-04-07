@echo off
REM Portainer 诊断脚本
REM 用于检查 Portainer 容器状态

echo ==================== Portainer 状态检查 ====================
echo.

echo [1/6] 检查 Portainer 容器状态...
ssh root@172.30.30.58 "docker ps -a | grep portainer"
echo.

echo [2/6] 检查 Portainer 日志（最近20行）...
ssh root@172.30.30.58 "docker logs portainer --tail 20"
echo.

echo [3/6] 检查端口监听状态...
ssh root@172.30.30.58 "netstat -tlnp | grep :9000"
echo.

echo [4/6] 检查防火墙状态...
ssh root@172.30.30.58 "firewall-cmd --list-ports 2>/dev/null || iptables -L -n | grep 9000"
echo.

echo [5/6] 检查 Docker 网络...
ssh root@172.30.30.58 "docker network ls"
echo.

echo [6/6] 测试 Portainer Web 服务...
ssh root@172.30.30.58 "curl -I http://localhost:9000 2>/dev/null | head -5"
echo.

echo ==================== 诊断完成 ====================
echo.
echo 可能的问题和解决方案：
echo.
echo 问题1: Portainer 容器未启动
echo 解决: ssh root@172.30.30.58 "docker start portainer"
echo.
echo 问题2: 端口未映射
echo 解决: 重新创建 Portainer 容器并映射端口
echo.
echo 问题3: 防火墙阻止
echo 解决: ssh root@172.30.30.58 "firewall-cmd --add-port=9000/tcp --permanent && firewall-cmd --reload"
echo.

pause
