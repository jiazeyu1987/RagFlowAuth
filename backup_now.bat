@echo off
setlocal
cd /d %~dp0

echo ==========================================
echo RagflowAuth - Backup (auth.db)
echo ==========================================
echo.

REM Uses the python in PATH; if you use conda, open "Anaconda Prompt" once to ensure PATH is correct.
python -m backend backup

echo.
pause

