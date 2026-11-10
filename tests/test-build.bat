@echo off
rem CMD: tests\test-build.bat  -  PowerShell: .\tests\test-build.bat
call "%~dp0..\ops\tests.bat" build
exit /b %ERRORLEVEL%
