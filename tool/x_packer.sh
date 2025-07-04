#!/bin/bash

# Path to virtual environment
VENV_PATH="../.venv"

# Activate the virtual environment
source "${VENV_PATH}/bin/activate"

SRC="../kcauto/__main__.py"
TARGET_PATH="../bin/kcauto_custom"

#remove old binaries
rm -rf ../bin
rm ../kcauto_custom
rm ../kcauto_cui

# Get the site-packages path from the virtual environment
PYTHON_SITE_PACKAGE=$(python -c "import site; print(site.getsitepackages()[0])")
echo "The Python site-packages directory is: $PYTHON_SITE_PACKAGE"

# Build the first executable
python -m PyInstaller --clean $SRC -p ../kcauto -p $PYTHON_SITE_PACKAGE --distpath $TARGET_PATH
mv "$TARGET_PATH/__main__/__main__" "$TARGET_PATH/__main__/kcauto_custom"
rm -r build
rm __main__.spec
ln -s "./bin/kcauto_custom/__main__/kcauto_custom" ../kcauto_custom


# Build the second executable
SRC="../kcauto/kcauto_cui.py"
TARGET_PATH="../bin/kcauto_cui"
python -m PyInstaller --clean $SRC -p ../kcauto/ -p $PYTHON_SITE_PACKAGE --distpath $TARGET_PATH
rm -r build
rm kcauto_cui.spec
ln -s "./bin/kcauto_cui/kcauto_cui/kcauto_cui" ../kcauto_cui

# Deactivate the virtual environment
deactivate