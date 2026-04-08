@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   RagflowAuth Server Backup Sync Tool
echo ========================================
echo.
echo Target:
echo   D:\Backups\RagflowAuth\from-test-server
echo.

powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0Sync-ServerBackups.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Sync complete.
) else (
    echo.
    echo Sync failed. Check:
    echo   %~dp0server-backup-sync.log
)

pause
