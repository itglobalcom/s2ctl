#!/bin/bash

BUNDLE_DIR=$(dirname `realpath $0`)
BUNDLE_PATH=$BUNDLE_DIR/dist/

cd $BUNDLE_DIR

echo ">>> PREPARE PYTHON VIRTUAL ENVIRONMENT"
python -m venv .venv
source .venv/bin/activate

(cd .. && poetry build)
rm -rf ./dist
mv -f ../dist ./

deactivate
rm -r ./.venv
echo "get your tarball and wheel in .\bundle\dist"
