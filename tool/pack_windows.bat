@echo off

:: Script #3: Execution pack script for Windows
:: Builds the executables, removes development-only files/folders,
:: and archives the entire folder as kcauto_custom_windows.zip.
::
:: Usage: run from the tool directory inside kcauto_custom_windows
::   cd tool && pack_windows.bat

setlocal enabledelayedexpansion

set "ROOT_PATH=..\"

:: Ensure script is run from .\tool
for %%I in ("%CD%") do set "CURRENT_DIR=%%~nxI"
if /i not "%CURRENT_DIR%"=="tool" (
	echo Error: must run this script from .\tool (current: %CD%)
	exit /b 1
)

:: ---------------------------------------------------------
:: Step 1: Build executables
:: ---------------------------------------------------------
echo Step 1: Building executables...
if not exist "exe_packer.bat" (
	echo Error: exe_packer.bat not found in %CD%
	exit /b 1
)
call exe_packer.bat
if errorlevel 1 (
	echo Error: exe_packer.bat failed
	exit /b 1
)

:: ---------------------------------------------------------
:: Step 2: Remove development-only files and folders
:: ---------------------------------------------------------
echo Step 2: Removing unnecessary files and folders...
cd "%ROOT_PATH%"

if exist ".git" rmdir /s /q ".git"
if exist ".github" rmdir /s /q ".github"
if exist ".venv" rmdir /s /q ".venv"
if exist "crash_screenshots" rmdir /s /q "crash_screenshots"
if exist "kcauto" rmdir /s /q "kcauto"
if exist "reference" rmdir /s /q "reference"
if exist ".gitignore" del /f /q ".gitignore"

:: ---------------------------------------------------------
:: Step 3: Create zip archive of the whole folder
:: ---------------------------------------------------------
echo Step 3: Creating zip archive...
for %%I in ("%CD%") do set "FOLDER_NAME=%%~nxI"
cd ..
powershell -Command "Compress-Archive -Path '%FOLDER_NAME%' -DestinationPath '%FOLDER_NAME%.zip' -Force"

echo.
echo ======================================================
echo Pack Complete!
echo  - %FOLDER_NAME%.zip
echo ======================================================
