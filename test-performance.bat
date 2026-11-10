@echo off
rem CMD: test-performance.bat  -  PowerShell: .\test-performance.bat
call "%~dp0ops\tests.bat" performance
exit /b %ERRORLEVEL%
