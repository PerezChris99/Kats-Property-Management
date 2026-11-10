@echo off
rem CMD: tests\test-e2e.bat  -  PowerShell: .\tests\test-e2e.bat
call "%~dp0..\ops\tests.bat" e2e
exit /b %ERRORLEVEL%
