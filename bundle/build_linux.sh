#!/bin/bash
set -euo pipefail

BUNDLE_DIR=$(dirname "$(realpath "$0")")
PROJECT_DIR=$(dirname "$BUNDLE_DIR")

if ! command -v poetry > /dev/null; then
    echo "poetry is required to build s2ctl: https://python-poetry.org/docs/#installation" >&2
    exit 1
fi

(cd "$PROJECT_DIR" && poetry install -q -n --no-ansi)

echo ">>> BUNDLING STARTED"

cd "$BUNDLE_DIR"
poetry run pyinstaller -y --clean --onefile -n s2ctl bundle.py
echo ">>> BUNDLE CREATED"

rm -rf ./build ./s2ctl.spec ./__pycache__
echo "get your bin in ./bundle/dist"
