@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
python -m vision --desktop
if errorlevel 1 pause
