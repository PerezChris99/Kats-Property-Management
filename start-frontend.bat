@echo off
rem Run from CMD as start-frontend.bat, or from PowerShell as .\start-frontend.bat
call "%~dp0ops\launch.bat" frontend %*
exit /b %ERRORLEVEL%
