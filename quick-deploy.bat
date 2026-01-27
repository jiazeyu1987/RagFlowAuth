@echo off
REM RagflowAuth Quick Deploy Script
REM Double-click this file to deploy with automatic version increment

echo ====================================
echo RagflowAuth Quick Deploy
echo ====================================
echo.
echo This will:
echo 1. Build Docker images (auto-increment version)
echo 2. Transfer to server
echo 3. Deploy on server
echo 4. Clean up old images
echo.
echo Press Ctrl+C to cancel, or
pause

cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File tool\scripts\deploy.ps1

echo.
echo ====================================
echo Deploy complete!
echo ====================================
pause
