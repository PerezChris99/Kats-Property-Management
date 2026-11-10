@echo off
rem CMD: tests\test-performance.bat  -  PowerShell: .\tests\test-performance.bat
call "%~dp0..\ops\tests.bat" performance
exit /b %ERRORLEVEL%
