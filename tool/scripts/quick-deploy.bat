@echo off
REM RagflowAuth Quick Deploy Launcher
REM Usage: Double-click to run or quick-deploy.bat

echo ========================================
echo RagflowAuth Quick Deploy
echo ========================================
echo.

REM Check if PowerShell is available
where pwsh >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PS=pwsh
) else (
    set PS=powershell
)

echo Running deployment script using %PS%...
echo.

REM Change to project root directory
cd /d "%~dp0..\.."

REM Run PowerShell script
%PS% -ExecutionPolicy Bypass -File "tool/scripts/quick-deploy.ps1" %*

echo.
echo Press any key to exit...
pause >nul
