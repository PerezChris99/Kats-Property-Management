@echo off
rem Run from CMD as create-owner.bat, or from PowerShell as .\create-owner.bat
call "%~dp0ops\launch.bat" owner %*
exit /b %ERRORLEVEL%
