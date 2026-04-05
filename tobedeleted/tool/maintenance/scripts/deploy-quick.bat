@echo off
REM RagflowAuth 快速部署脚本
REM 这是一个简化的部署脚本，使用默认配置一键部署

echo ========================================
echo   RagflowAuth 快速部署工具
echo ========================================
echo.

REM 检查 deploy.ps1 是否存在
if not exist "%~dp0deploy.ps1" (
    echo 错误: 找不到 deploy.ps1
    echo.
    pause
    exit /b 1
)

echo 即将开始部署到服务器 172.30.30.57
echo.
echo 此脚本将:
echo   1. 构建前端和后端 Docker 镜像
echo   2. 导出镜像为 tar 文件
echo   3. 传输到服务器
echo   4. 在服务器上加载并启动容器
echo.
echo 按任意键继续，或按 Ctrl+C 取消...
pause > nul

echo.
echo [1/4] 开始部署...
echo.

REM 执行 PowerShell 部署脚本
powershell.exe -ExecutionPolicy Bypass -File "%~dp0deploy.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   部署成功！
    echo ========================================
    echo.
    echo 访问地址:
    echo   前端: http://172.30.30.57:3001
    echo   后端: http://172.30.30.57:8001
    echo.
) else (
    echo.
    echo ========================================
    echo   部署失败，请检查错误信息
    echo ========================================
    echo.
)

pause
