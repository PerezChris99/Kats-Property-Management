@echo off
rem Run from CMD as stop.bat, or from PowerShell as .\stop.bat
call "%~dp0ops\launch.bat" stop %*
exit /b %ERRORLEVEL%
