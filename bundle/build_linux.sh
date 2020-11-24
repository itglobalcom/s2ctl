#!/bin/bash

BUNDLE_DIR=$(dirname `realpath $0`)
BUNDLE_PATH=$BUNDLE_DIR/dist/

pip install "pyinstaller<=2.1"
pip install poetry
poetry install -q -n --no-ansi

echo ">>> BUNDLING STARTED"

cd $BUNDLE_DIR 
pyinstaller -y --clean --add-binary '/usr/lib/libc.so:.' --onefile -n s2ctl bundle.py
echo ">>> BUNDLE CREATED"

deactivate
rm -r ./build ./s2ctl.spec ./__pycache__
echo "get your bin in .\bundle\dist"
