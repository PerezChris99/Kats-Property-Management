@echo off
rem Run from CMD as start-backend.bat, or from PowerShell as .\start-backend.bat
set "KATS_FAST_START=1"
call "%~dp0ops\launch.bat" backend %*
exit /b %ERRORLEVEL%
