@echo off
REM Double-click this file to run the app.
REM Requires Python to be installed (python.org, check "Add Python to PATH").

echo [1/2] Installing required packages (skips if already installed)...
pip install -r requirements.txt

echo [2/2] Starting the app...
python app.py

pause
