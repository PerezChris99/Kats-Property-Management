@echo off
rem CMD: test-api.bat  -  PowerShell: .\test-api.bat
call "%~dp0ops\tests.bat" api
exit /b %ERRORLEVEL%
