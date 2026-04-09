#!/bin/bash

# Path to virtual environment
VENV_PATH="../.venv"

# Activate the virtual environment
source "${VENV_PATH}/bin/activate"

SRC="../kcauto/__main__.py"
ROOT_PATH="../"
BIN_PATH="../bin"
rm -f "../kcauto_custom"
rm -rf "${BIN_PATH}/kcauto_custom"

# Get the site-packages path from the virtual environment
PYTHON_SITE_PACKAGE=$(python -c "import site; print(site.getsitepackages()[0])")
echo "The Python site-packages directory is: $PYTHON_SITE_PACKAGE"


# Build the first executable
python -m PyInstaller -D --clean $SRC -p ../kcauto -p $PYTHON_SITE_PACKAGE --distpath $BIN_PATH --name "kcauto_custom"
rm -r dist
rm -r build
rm __main__.spec

strip "${BIN_PATH}/kcauto_custom/kcauto_custom"
ln -sf "bin/kcauto_custom/kcauto_custom" "${ROOT_PATH}kcauto_custom"

# Build the second executable
SRC="../kcauto/kcauto_cui.py"
rm -f "../kcauto_cui"
rm -rf "${BIN_PATH}/kcauto_cui"
python -m PyInstaller -D --clean $SRC -p ../kcauto/ -p $PYTHON_SITE_PACKAGE --distpath $BIN_PATH --name "kcauto_cui"
rm -r dist
rm -r build
rm kcauto_cui.spec

strip "${BIN_PATH}/kcauto_cui/kcauto_cui"
ln -sf "bin/kcauto_cui/kcauto_cui" "${ROOT_PATH}kcauto_cui"

# Deactivate the virtual environment
deactivate