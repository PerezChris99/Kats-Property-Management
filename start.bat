@echo off
rem Direct launch: backend LEFT, frontend RIGHT in Windows Terminal.
rem Inside VS Code use Terminal > Run Task > KATS: Native start (split in VS Code)
rem to get two VS Code integrated terminal panes instead.
set "KATS_FAST_START=1"
call "%~dp0ops\launch.bat" split %*
exit /b %ERRORLEVEL%
