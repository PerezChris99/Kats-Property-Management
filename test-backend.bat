@echo off
rem CMD: test-backend.bat  -  PowerShell: .\test-backend.bat
call "%~dp0ops\tests.bat" backend
exit /b %ERRORLEVEL%
