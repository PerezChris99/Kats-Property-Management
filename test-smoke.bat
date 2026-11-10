@echo off
rem CMD: test-smoke.bat  -  PowerShell: .\test-smoke.bat
call "%~dp0ops\tests.bat" smoke
exit /b %ERRORLEVEL%
