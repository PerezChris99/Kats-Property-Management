@echo off
rem CMD: test-all.bat  -  PowerShell: .\test-all.bat
call "%~dp0ops\tests.bat" all
exit /b %ERRORLEVEL%
