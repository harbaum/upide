#!/bin/bash
# Needed in preparation:
# wget https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
# wine python-3.10.11-amd64.exe
# wine "$PY"/Scripts/pip.exe install pyinstaller pyqt5 pyserial
PY=~/.wine/drive_c/users/$USER/AppData/Local/Programs/Python/Python310
if [ ! -f "$PY/python.exe" ]; then
    echo "$PY/python.exe does not exist."
    PY=~/.wine/drive_c/users/$USER/Local\ Settings/Application\ Data/Programs/Python/Python310
fi

wine "${PY}/python.exe" -m PyInstaller --clean --icon=upide.ico --windowed --onefile --add-data='assets;assets' upide.py
