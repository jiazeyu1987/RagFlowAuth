@echo off
setlocal
cd /d %~dp0
python scripts\run_realdata_e2e.py --strict
exit /b %ERRORLEVEL%
