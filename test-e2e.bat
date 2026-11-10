@echo off
rem CMD: test-e2e.bat  -  PowerShell: .\test-e2e.bat
call "%~dp0ops\tests.bat" e2e
exit /b %ERRORLEVEL%
