@echo off
REM Run this file on a PC that HAS Python installed.
REM The resulting exe can then be copied to any PC, even one without Python.

echo [1/3] Installing required packages...
pip install -r requirements.txt

echo [2/3] Building exe... (this may take a few minutes)
pyinstaller --noconfirm --onefile --windowed --name RecordingSummarizer app.py

echo [3/3] Done. Check the dist folder for RecordingSummarizer.exe
echo Copy that one exe file to any PC to run it there - no Python needed on that PC.
pause
