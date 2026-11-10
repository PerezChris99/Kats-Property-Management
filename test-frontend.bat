@echo off
rem CMD: test-frontend.bat  -  PowerShell: .\test-frontend.bat
call "%~dp0ops\tests.bat" frontend
exit /b %ERRORLEVEL%
