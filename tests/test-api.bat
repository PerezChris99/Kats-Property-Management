@echo off
rem CMD: tests\test-api.bat  -  PowerShell: .\tests\test-api.bat
call "%~dp0..\ops\tests.bat" api
exit /b %ERRORLEVEL%
