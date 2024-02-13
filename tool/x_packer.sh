#!/bin/sh

SRC="../kcauto/__main__.py"
TARGET_PATH="../kcauto.bin"

# store the output of the python command in a variable
PYTHON_SITE_PACKAGE=$(python3.7 -m site --user-site)
echo The Python site-packages directory is: $PYTHON_SITE_PACKAGE

python3.7 -m PyInstaller -F $SRC -p ../kcauto -p $PYTHON_SITE_PACKAGE
mv ./dist/__main__ $TARGET_PATH
rm -r dist
rm -r build
rm __main__.spec

SRC="../kcauto/kcauto_cui.py"
TARGET_PATH="../kcauto_cui"
python3.7 -m PyInstaller -F $SRC -p ../kcauto/ -p $PYTHON_SITE_PACKAGE
mv ./dist/kcauto_cui $TARGET_PATH
rm -r dist
rm -r build
rm kcauto_cui.spec