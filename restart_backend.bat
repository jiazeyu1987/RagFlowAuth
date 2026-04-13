@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "BACKEND_PORT=8001"
set "BACKEND_HOST=0.0.0.0"
set "BACKEND_TITLE=RagflowAuth Backend"
set "BACKEND_ROOT=%CD%"
set "JWT_SECRET_VALUE="

call :resolve_jwt_secret
if errorlevel 1 exit /b 1

echo [INFO] Restarting backend on port %BACKEND_PORT% ...
call :stop_port_processes %BACKEND_PORT%

echo [INFO] Starting backend on port %BACKEND_PORT% ...
start "%BACKEND_TITLE%" cmd /k cd /d "%BACKEND_ROOT%" ^&^& python -m backend run --host %BACKEND_HOST% --port %BACKEND_PORT%

exit /b 0

:resolve_jwt_secret
if defined JWT_SECRET_KEY (
  set "JWT_SECRET_VALUE=%JWT_SECRET_KEY%"
)

if not defined JWT_SECRET_VALUE (
  for /f "usebackq tokens=1* delims==" %%A in (".env") do (
    if /I "%%A"=="JWT_SECRET_KEY" (
      set "JWT_SECRET_VALUE=%%B"
    )
  )
)

if not defined JWT_SECRET_VALUE (
  echo [ERROR] Missing JWT_SECRET_KEY. Set it in the current shell or in .env before restarting backend.
  exit /b 1
)

if "%JWT_SECRET_VALUE%"=="your-secret-key-change-in-production" (
  echo [ERROR] JWT_SECRET_KEY is still using the default insecure value. Update it before restarting backend.
  exit /b 1
)

exit /b 0

:stop_port_processes
set "PORT_TO_STOP=%~1"
set "FOUND_PID="

for /f "tokens=5" %%P in ('netstat -ano -p tcp ^| findstr /R /C:":%PORT_TO_STOP% .*LISTENING"') do (
  set "FOUND_PID=1"
  echo [INFO] Stopping PID %%P listening on port %PORT_TO_STOP% ...
  taskkill /PID %%P /F >nul 2>&1
)

if not defined FOUND_PID (
  echo [INFO] No listening process found on port %PORT_TO_STOP%.
  exit /b 0
)

call :wait_for_port_release %PORT_TO_STOP%
exit /b %errorlevel%

:wait_for_port_release
set "PORT_TO_WAIT=%~1"

for /L %%I in (1,1,15) do (
  netstat -ano -p tcp | findstr /R /C:":%PORT_TO_WAIT% .*LISTENING" >nul
  if errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)

echo [ERROR] Port %PORT_TO_WAIT% is still in use after waiting.
exit /b 1
