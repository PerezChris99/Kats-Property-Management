@echo off
rem Run from CMD as start.bat, or from PowerShell as .\start.bat
call "%~dp0ops\launch.bat" start %*
exit /b %ERRORLEVEL%
