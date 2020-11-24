poetry shell
poetry install -n --no-ansi
cd bundle ; pyinstaller -y --clean --onefile -n s2ctl bundle.py ; cd ..
