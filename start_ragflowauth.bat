@echo off
setlocal
cd /d "%~dp0"

set "BACKEND_PORT=8001"
set "BACKEND_HOST=0.0.0.0"
set "FRONTEND_PORT=3001"
set "OPEN_URL=http://127.0.0.1:%FRONTEND_PORT%/chat"
set "JWT_SECRET_VALUE="

call :is_listening %BACKEND_PORT%
if errorlevel 1 (
  call :resolve_jwt_secret
  if errorlevel 1 exit /b 1
  echo [INFO] Starting backend on port %BACKEND_PORT% ...
  start "RagflowAuth Backend" cmd /k "cd /d ""%~dp0"" && python -m backend run --host %BACKEND_HOST% --port %BACKEND_PORT%"
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

:resolve_jwt_secret
if defined JWT_SECRET_KEY (
  set "JWT_SECRET_VALUE=%JWT_SECRET_KEY%"
)

if not defined JWT_SECRET_VALUE if exist ".env" (
  for /f "usebackq tokens=1* delims==" %%A in (".env") do (
    if /I "%%A"=="JWT_SECRET_KEY" (
      set "JWT_SECRET_VALUE=%%B"
    )
  )
)

if not defined JWT_SECRET_VALUE (
  echo [ERROR] Missing JWT_SECRET_KEY. Set it in the current shell or in .env before starting backend.
  exit /b 1
)

if "%JWT_SECRET_VALUE%"=="your-secret-key-change-in-production" (
  echo [ERROR] JWT_SECRET_KEY is still using the default insecure value. Update it before starting backend.
  exit /b 1
)

exit /b 0

:is_listening
set "PORT_TO_CHECK=%~1"
netstat -ano -p tcp | findstr /R /C:":%PORT_TO_CHECK% .*LISTENING" >nul
if %errorlevel%==0 (
  exit /b 0
)
exit /b 1
