#!/bin/bash
python3 -m PyInstaller --noconfirm --windowed --onefile --name="upide-linux" --add-data='assets:assets' upide.py
