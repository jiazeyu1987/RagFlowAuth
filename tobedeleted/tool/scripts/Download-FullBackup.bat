@echo off
REM RagflowAuth 全量备份下载脚本 - 双击运行
REM 用途：从服务器下载最新的全量备份包到本地

chcp 65001 >nul
echo.
echo ========================================
echo   RagflowAuth 全量备份下载工具
echo ========================================
echo.
echo 正在启动下载脚本...
echo.

powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0Download-FullBackup.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   下载完成！
    echo ========================================
    echo.
    echo 备份文件保存在: D:\datas\
    echo.
) else (
    echo.
    echo ========================================
    echo   下载失败！
    echo ========================================
    echo.
    echo 请查看日志文件: %~dp0full-backup-download.log
    echo.
)

pause
