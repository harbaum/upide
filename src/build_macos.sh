#!/bin/bash
python3 -m PyInstaller --noconfirm --windowed --name="upide" --icon=icon.icns --add-data='assets:assets' upide.py
mkdir -p dist/dmg
rm -r dist/dmg/*
cp -r dist/upide.app dist/dmg
test -f "dist/upide.dmg" && rm "dist/upide.dmg"
create-dmg \
  --volname "uPIDE" \
  --volicon "icon.icns" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 100 \
  --icon "upide.app" 175 120 \
  --hide-extension "upide.app" \
  --app-drop-link 425 120 \
  "dist/upide.dmg" \
  "dist/dmg/"
