@echo off
REM RagflowAuth 备份下载脚本（通用版）- 双击运行
REM 用途：自动下载最新的备份包（增量或全量）

chcp 65001 >nul
echo.
echo ========================================
echo   RagflowAuth 备份下载工具（通用）
echo ========================================
echo.
echo 将自动选择最新的备份包（增量或全量）
echo.
echo 正在启动下载脚本...
echo.

powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0Download-Backup.ps1"

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
    echo 请查看日志文件: %~dp0backup-download.log
    echo.
)

pause
