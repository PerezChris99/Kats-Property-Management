@echo off
rem Run from CMD as start-frontend.bat, or from PowerShell as .\start-frontend.bat
set "KATS_FAST_START=1"
call "%~dp0ops\launch.bat" frontend %*
exit /b %ERRORLEVEL%
