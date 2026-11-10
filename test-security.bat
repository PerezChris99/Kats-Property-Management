@echo off
rem CMD: test-security.bat  -  PowerShell: .\test-security.bat
call "%~dp0ops\tests.bat" security
exit /b %ERRORLEVEL%
