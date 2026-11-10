@echo off
rem Run from CMD as start-backend.bat, or from PowerShell as .\start-backend.bat
call "%~dp0ops\launch.bat" backend %*
exit /b %ERRORLEVEL%
