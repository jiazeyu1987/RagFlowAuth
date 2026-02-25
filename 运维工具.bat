@echo off
setlocal
chcp 65001 >nul

set "ROOT=%~dp0"
set "CONDA_ROOT=D:\miniconda3"
set "TOOL_PY=%ROOT%tool\maintenance\tool.py"

if not exist "%TOOL_PY%" (
  echo [ERROR] tool.py not found: %TOOL_PY%
  pause
  exit /b 1
)

if not exist "%CONDA_ROOT%\Scripts\activate.bat" (
  echo [ERROR] Conda activate script not found: %CONDA_ROOT%\Scripts\activate.bat
  pause
  exit /b 1
)

call "%CONDA_ROOT%\Scripts\activate.bat" "%CONDA_ROOT%"
call conda activate base
if errorlevel 1 (
  echo [ERROR] Failed to activate conda base environment.
  pause
  exit /b 1
)

python "%TOOL_PY%"
set "CODE=%ERRORLEVEL%"

if not "%CODE%"=="0" (
  echo [ERROR] tool.py exited with code %CODE%
  pause
)

exit /b %CODE%

