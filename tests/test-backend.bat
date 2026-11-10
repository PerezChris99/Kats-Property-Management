@echo off
rem CMD: tests\test-backend.bat  -  PowerShell: .\tests\test-backend.bat
call "%~dp0..\ops\tests.bat" backend
exit /b %ERRORLEVEL%
