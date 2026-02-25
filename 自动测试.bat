@echo off
setlocal
chcp 65001 >nul

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo [START] Running fullstack automated tests...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\run_fullstack_tests.ps1"
set "CODE=%ERRORLEVEL%"

if "%CODE%"=="0" (
  echo [DONE] Tests completed (PASS)
) else (
  echo [DONE] Tests completed (FAIL, exit code=%CODE%)
)

echo Report path:
echo   %ROOT%doc\test\reports\fullstack_test_report_latest.md
start "" "%ROOT%doc\test\reports\fullstack_test_report_latest.md"

echo.
pause
exit /b %CODE%
