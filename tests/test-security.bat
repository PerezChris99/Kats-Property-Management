@echo off
rem CMD: tests\test-security.bat  -  PowerShell: .\tests\test-security.bat
call "%~dp0..\ops\tests.bat" security
exit /b %ERRORLEVEL%
