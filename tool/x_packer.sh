#!/bin/bash

# Path to virtual environment
VENV_PATH="../.venv"

# Activate the virtual environment
source "${VENV_PATH}/bin/activate"

SRC="../kcauto/__main__.py"
TARGET_PATH="../kcauto.bin"

# Get the site-packages path from the virtual environment
PYTHON_SITE_PACKAGE=$(python -c "import site; print(site.getsitepackages()[0])")
echo "The Python site-packages directory is: $PYTHON_SITE_PACKAGE"

# Build the first executable
python -m PyInstaller -F --clean $SRC -p ../kcauto -p $PYTHON_SITE_PACKAGE
mv ./dist/__main__ $TARGET_PATH
rm -r dist
rm -r build
rm __main__.spec

strip $TARGET_PATH

# Build the second executable
SRC="../kcauto/kcauto_cui.py"
TARGET_PATH="../kcauto_cui"
python -m PyInstaller -F --clean $SRC -p ../kcauto/ -p $PYTHON_SITE_PACKAGE
mv ./dist/kcauto_cui $TARGET_PATH
rm -r dist
rm -r build
rm kcauto_cui.spec

strip $TARGET_PATH

# Deactivate the virtual environment
deactivate