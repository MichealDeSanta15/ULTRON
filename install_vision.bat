@echo off
setlocal
cd /d "%~dp0"
python -m pip install --upgrade pip
python -m pip install -e .
echo.
echo VISION is installed. Run run_vision.bat to launch it.
pause
