@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onedir --windowed --name "BamBuddy-Label-Printer" --add-data "src\translations.json;." --add-data "assets\app_icon.ico;." --icon "assets\app_icon.ico" --paths src --collect-all niimbot_b1 --collect-all bleak --collect-all keyring src\main.py
pause
