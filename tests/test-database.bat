@echo off
rem CMD: tests\test-database.bat  -  PowerShell: .\tests\test-database.bat
call "%~dp0..\ops\tests.bat" database
exit /b %ERRORLEVEL%
