@echo off
rem CMD: tests\test-frontend.bat  -  PowerShell: .\tests\test-frontend.bat
call "%~dp0..\ops\tests.bat" frontend
exit /b %ERRORLEVEL%
