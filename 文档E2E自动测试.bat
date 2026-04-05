@echo off
setlocal
chcp 65001 >nul

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo [START] Running doc/e2e automated tests...
python "%ROOT%scripts\run_doc_e2e.py" --repo-root "%ROOT%"
set "CODE=%ERRORLEVEL%"

if "%CODE%"=="0" (
  echo [DONE] Doc E2E completed (PASS)
) else (
  echo [DONE] Doc E2E completed (FAIL, exit code=%CODE%)
)

echo Report path:
echo   %ROOT%doc\test\reports\doc_e2e_report_latest.md
start "" "%ROOT%doc\test\reports\doc_e2e_report_latest.md"

echo.
pause
exit /b %CODE%
