#!/bin/bash

VENV_PATH="../.venv"
BIN_PATH="../bin"
ROOT_PATH="../"

# Ensure script is run from ./tool
if [ "$(basename "$PWD")" != "tool" ]; then
	echo "Error: must run this script from ./tool (current: $PWD)"
	exit 1
fi

# Activate the virtual environment
source "${VENV_PATH}/bin/activate"

# Get the site-packages path from the virtual environment
PYTHON_SITE_PACKAGE=$(python -c "import site; print(site.getsitepackages()[0])")
echo "Python site-packages: $PYTHON_SITE_PACKAGE"

# ---------------------------------------------------------
# 1. Build core executable (placed in bin/)
# ---------------------------------------------------------
SRC_CUSTOM="../kcauto/__main__.py"
rm -rf "${BIN_PATH}/kcauto_custom"

echo "Building Core: kcauto_custom..."
python -m PyInstaller -D --clean $SRC_CUSTOM -p ../kcauto/ -p $PYTHON_SITE_PACKAGE --distpath $BIN_PATH --name "kcauto_custom"
 
# Create a soft link in ../kcauto pointing to the built kcauto_custom
TARGET_LINK="../kcauto_custom"
if [ -e "${BIN_PATH}/kcauto_custom/kcauto_custom" ]; then
	if [ -L "$TARGET_LINK" ] || [ -e "$TARGET_LINK" ]; then
		rm -f "$TARGET_LINK"
	fi
	ln -s "./bin/kcauto_custom/kcauto_custom" "$TARGET_LINK"
	echo "Created symlink: $TARGET_LINK -> ./bin/kcauto_custom/kcauto_custom"
else
	echo "Warning: ${BIN_PATH}/kcauto_custom/kcauto_custom not found; skipping symlink creation"
fi

# ---------------------------------------------------------
# 2. Build CUI launcher (single file, placed in root directory)
# ---------------------------------------------------------
SRC_CUI="../kcauto/kcauto_cui.py"
rm -f "${ROOT_PATH}kcauto_cui"

echo "Building Launcher: kcauto_cui..."
python -m PyInstaller -F --clean $SRC_CUI -p ../kcauto/ -p $PYTHON_SITE_PACKAGE --distpath $ROOT_PATH --name "kcauto_cui"

# ---------------------------------------------------------
# 3. Clean up temporary files
# ---------------------------------------------------------
echo "Cleaning up temporary files..."
rm -rf ./dist
rm -rf ./build
rm -f ./__main__.spec
rm -f ./kcauto_cui.spec

# Deactivate the virtual environment
deactivate

echo ""
echo "======================================================"
echo "Build Complete!"
echo "Root Directory:"
echo " - kcauto_cui     (Launcher/Console)"
echo "======================================================"
