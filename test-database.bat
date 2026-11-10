@echo off
rem CMD: test-database.bat  -  PowerShell: .\test-database.bat
call "%~dp0ops\tests.bat" database
exit /b %ERRORLEVEL%
