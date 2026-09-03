poetry install -n --no-ansi
cd bundle && poetry run pyinstaller -y --clean --onefile -n s2ctl bundle.py && cd ..
