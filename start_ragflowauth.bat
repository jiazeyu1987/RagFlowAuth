@echo off
setlocal
cd /d "%~dp0"

set "BACKEND_PORT=8001"
set "FRONTEND_PORT=3001"
set "OPEN_URL=http://127.0.0.1:%FRONTEND_PORT%/chat"

call :is_listening %BACKEND_PORT%
if errorlevel 1 (
  echo [INFO] Starting backend on port %BACKEND_PORT% ...
  start "RagflowAuth Backend" cmd /k "cd /d ""%~dp0"" && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port %BACKEND_PORT%"
) else (
  echo [INFO] Backend already listening on port %BACKEND_PORT%.
)

call :is_listening %FRONTEND_PORT%
if errorlevel 1 (
  echo [INFO] Starting frontend on port %FRONTEND_PORT% ...
  start "RagflowAuth Frontend" cmd /k "cd /d ""%~dp0fronted"" && set ""PORT=%FRONTEND_PORT%"" && set ""BROWSER=none"" && npm start"
) else (
  echo [INFO] Frontend already listening on port %FRONTEND_PORT%.
)

echo [INFO] Opening %OPEN_URL%
start "" "%OPEN_URL%"
exit /b 0

:is_listening
set "PORT_TO_CHECK=%~1"
netstat -ano -p tcp | findstr /R /C:":%PORT_TO_CHECK% .*LISTENING" >nul
if %errorlevel%==0 (
  exit /b 0
)
exit /b 1
