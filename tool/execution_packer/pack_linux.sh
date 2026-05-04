#!/bin/bash

# Script #2: Execution pack script for Linux
# Builds the executables, removes development-only files/folders,
# and archives the entire folder as kcauto_custom_linux.tar.
#
# Usage: run from the execution_packer directory inside kcauto_custom_linux
#   cd tool/execution_packer && bash pack_linux.sh

ROOT_PATH="../../"

# Ensure script is run from ./tool/execution_packer
if [ "$(basename "$PWD")" != "execution_packer" ]; then
	echo "Error: must run this script from ./tool/execution_packer (current: $PWD)"
	exit 1
fi

# ---------------------------------------------------------
# Step 1: Build executables
# ---------------------------------------------------------
echo "Step 1: Building executables..."
if [ ! -f "x_packer.sh" ]; then
	echo "Error: x_packer.sh not found in $(pwd)"
	exit 1
fi
bash x_packer.sh
if [ $? -ne 0 ]; then
	echo "Error: x_packer.sh failed"
	exit 1
fi

# ---------------------------------------------------------
# Step 2: Remove development-only files and folders
# ---------------------------------------------------------
echo "Step 2: Removing unnecessary files and folders..."
cd "$ROOT_PATH" || exit 1

rm -rf .git
rm -rf .github
rm -rf .venv
rm -rf crash_screenshots
rm -rf kcauto
rm -rf reference
rm -f .gitignore

# ---------------------------------------------------------
# Step 3: Create tar archive of the whole folder
# ---------------------------------------------------------
echo "Step 3: Creating tar archive..."
FOLDER_NAME=$(basename "$PWD")
cd .. || exit 1
tar -czf "${FOLDER_NAME}.tar.gz" "${FOLDER_NAME}"

echo ""
echo "======================================================"
echo "Pack Complete!"
echo " - $(realpath "${FOLDER_NAME}.tar.gz")"
echo "======================================================"
