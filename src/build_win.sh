#!/bin/bash
# Needed in preparation:
# wget https://www.python.org/ftp/python/3.9.5/python-3.9.5-amd64.exe
# wine python-3.9.5-amd64.exe
# wine "$PY"/Scripts/pip install pyinstaller pyqt5 pyserial
PY=~/.wine/drive_c/users/$USER/Local\ Settings/Application\ Data/Programs/Python/Python39
wine "${PY}/python" -m PyInstaller --clean --icon=upide.ico --windowed --onefile --add-data='assets;assets' upide.py
