#!/bin/bash

# Script #1: Create workspace for kcauto_custom release build
# Creates kcauto_custom_release folder outside the repo root,
# clones the repo into kcauto_custom_linux and kcauto_custom_windows,
# and switches each to the corresponding branch.
#
# Usage: run from the execution_packer directory
#   cd tool/execution_packer && bash setup_release.sh

REPO_URL="https://github.com/XVs32/kcauto_custom/"
RELEASE_DIR="../../../kcauto_custom_release"

# Ensure script is run from ./tool/execution_packer
if [ "$(basename "$PWD")" != "execution_packer" ]; then
	echo "Error: must run this script from ./tool/execution_packer (current: $PWD)"
	exit 1
fi

# Create or clean the release directory
if [ -d "$RELEASE_DIR" ]; then
	echo "Cleaning existing release directory: $(realpath "$RELEASE_DIR")"
	rm -rf "$RELEASE_DIR"
fi
mkdir -p "$RELEASE_DIR"

# Clone kcauto_custom and name it kcauto_custom_linux
echo "Cloning $REPO_URL into kcauto_custom_linux..."
git clone "$REPO_URL" "$RELEASE_DIR/kcauto_custom_linux"

# If a .venv exists in the current workspace, copy it into kcauto_custom_linux
VENV_SRC="../../.venv"
if [ -d "$VENV_SRC" ]; then
	echo "Copying .venv to kcauto_custom_linux..."
	cp -r "$VENV_SRC" "$RELEASE_DIR/kcauto_custom_linux/.venv"
else
	echo "No .venv found in workspace; skipping."
fi

# Copy kcauto_custom_linux to kcauto_custom_windows
echo "Copying kcauto_custom_linux to kcauto_custom_windows..."
cp -r "$RELEASE_DIR/kcauto_custom_linux" "$RELEASE_DIR/kcauto_custom_windows"

# Switch kcauto_custom_linux to develop_linux branch
echo "Switching kcauto_custom_linux to branch: develop_linux..."
cd "$RELEASE_DIR/kcauto_custom_linux" || exit 1
git checkout develop_linux
cd - > /dev/null || exit 1

# Switch kcauto_custom_windows to develop_windows branch
echo "Switching kcauto_custom_windows to branch: develop_windows..."
cd "$RELEASE_DIR/kcauto_custom_windows" || exit 1
git checkout develop_windows
cd - > /dev/null || exit 1

echo ""
echo "======================================================"
echo "Workspace Setup Complete!"
echo " - Linux:   $(realpath "$RELEASE_DIR/kcauto_custom_linux") (branch: develop_linux)"
echo " - Windows: $(realpath "$RELEASE_DIR/kcauto_custom_windows") (branch: develop_windows)"
echo "======================================================"
