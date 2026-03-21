@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_ragflowauth.ps1"
exit /b %errorlevel%
