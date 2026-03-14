@echo off
setlocal
set SCRIPT_DIR=%~dp0
wscript //nologo "%SCRIPT_DIR%start_fullstack.vbs" %*
endlocal
