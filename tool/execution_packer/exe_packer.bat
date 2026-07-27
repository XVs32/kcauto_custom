@echo off

setlocal enabledelayedexpansion



set "VENV_PATH=..\..\.venv"

set "BIN_PATH=..\..\bin"

set "ROOT_PATH=..\..\"



:: 啟動虛擬環境

call "%VENV_PATH%\Scripts\activate.bat"



:: 取得 site-packages 路徑

for /f "delims=" %%i in ('python -c "import site; print(site.getsitepackages()[0])"') do set "python_site_package=%%i"

echo Python site-packages: %python_site_package%



:: ---------------------------------------------------------

:: 1. 編譯核心 GUI 程式 (放在 bin 資料夾)

:: ---------------------------------------------------------

set "src_custom=..\..\kcauto\__main__.py"

if exist "%BIN_PATH%\kcauto_custom" rmdir /s /q "%BIN_PATH%\kcauto_custom"



echo Building Core: kcauto_custom...

python -m PyInstaller -D --clean %src_custom% -p ..\..\kcauto\ -p %python_site_package% --distpath %BIN_PATH% --name "kcauto_custom"



:: ---------------------------------------------------------

:: 2. 編譯 CUI 啟動器 (放在根目錄，指向 bin 內的執行檔)

:: ---------------------------------------------------------

set "src_cui=..\..\kcauto\kcauto_cui.py"

set "icon_path=..\..\assets\cui\bot.ico"

echo Building Launcher: kcauto_cui with icon...
:: 加入 --icon "%icon_path%"
python -m PyInstaller -F --clean --icon "%icon_path%" %src_cui% -p ..\..\kcauto\ -p %python_site_package% --distpath %ROOT_PATH% --name "kcauto_cui"


:: ---------------------------------------------------------

:: 3. 清理臨時檔案

:: ---------------------------------------------------------

echo Cleaning up temporary files...

rmdir /s /q ".\dist"

rmdir /s /q ".\build"

del .\__main__.spec

del .\kcauto_cui.spec



:: 停用虛擬環境

call "%VENV_PATH%\Scripts\deactivate.bat"



echo.

echo ======================================================

echo Build Complete!

echo Root Directory:

echo  - kcauto_cui.exe    (Launcher/Console)

echo ======================================================

pause