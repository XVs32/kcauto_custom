#!/bin/bash

# Path to virtual environment
VENV_PATH="../.venv"

# Activate the virtual environment
source "${VENV_PATH}/bin/activate"

SRC="../kcauto/__main__.py"
TARGET_PATH="../"
rm -r "../kcauto_custom"

# Get the site-packages path from the virtual environment
PYTHON_SITE_PACKAGE=$(python -c "import site; print(site.getsitepackages()[0])")
echo "The Python site-packages directory is: $PYTHON_SITE_PACKAGE"


# Build the first executable
python -m PyInstaller -F --clean $SRC -p ../kcauto -p $PYTHON_SITE_PACKAGE --distpath $TARGET_PATH --name "kcauto_custom"
rm -r dist
rm -r build
rm __main__.spec

strip "../kcauto_custom"

# Build the second executable
SRC="../kcauto/kcauto_cui.py"
TARGET_PATH="../"
rm -r "../kcauto_cui"
python -m PyInstaller -F --clean $SRC -p ../kcauto/ -p $PYTHON_SITE_PACKAGE --distpath $TARGET_PATH --name "kcauto_cui"
rm -r dist
rm -r build
rm kcauto_cui.spec

strip "../kcauto_cui"

# Deactivate the virtual environment
deactivate