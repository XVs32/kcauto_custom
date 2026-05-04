@echo off

:: Script #3: Execution pack script for Windows
:: Builds the executables, removes development-only files/folders,
:: and archives the entire folder as kcauto_custom_windows.zip.
::
:: Usage: run from anywhere - paths are derived from the script's location
::   tool\execution_packer\pack_windows.bat

setlocal enabledelayedexpansion

:: Derive paths from the script's own location (%~dp0) so the script
:: works correctly regardless of the current working directory.
set "TOOL_DIR=%~dp0"
if "%TOOL_DIR:~-1%"=="\" set "TOOL_DIR=%TOOL_DIR:~0,-1%"
for %%I in ("%TOOL_DIR%\..\..\") do set "ROOT_DIR=%%~fI"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

echo ======================================================
echo Execution Pack Script - Windows
echo Tool Dir : %TOOL_DIR%
echo Root Dir : %ROOT_DIR%
echo ======================================================

:: ---------------------------------------------------------
:: Step 1: Build executables via exe_packer.bat
:: ---------------------------------------------------------
echo.
echo [Step 1] Building executables...
cd /d "%TOOL_DIR%"
if not exist "exe_packer.bat" (
    echo Error: exe_packer.bat not found in %TOOL_DIR%
    exit /b 1
)
call exe_packer.bat

:: ---------------------------------------------------------
:: Step 2: Remove development-only files and folders
:: ---------------------------------------------------------
echo.
echo [Step 2] Removing unnecessary files and folders...
cd /d "%ROOT_DIR%"

if exist ".git"              rmdir /s /q ".git"
if exist ".github"           rmdir /s /q ".github"
if exist ".venv"             rmdir /s /q ".venv"
if exist "crash_screenshots" rmdir /s /q "crash_screenshots"
if exist "kcauto"            rmdir /s /q "kcauto"
if exist "reference"         rmdir /s /q "reference"
if exist ".gitignore"        del /f /q ".gitignore"

:: ---------------------------------------------------------
:: Step 3: Create zip archive of the whole folder
:: ---------------------------------------------------------
echo.
echo [Step 3] Creating zip archive...
for %%I in ("%ROOT_DIR%") do set "FOLDER_NAME=%%~nxI"
for %%I in ("%ROOT_DIR%\..") do set "PARENT_DIR=%%~fI"
cd /d "%PARENT_DIR%"
powershell -NoProfile -Command "Compress-Archive -Path '%FOLDER_NAME%' -DestinationPath '%FOLDER_NAME%.zip' -Force"
if errorlevel 1 (
    echo Error: Failed to create zip archive
    exit /b 1
)

echo.
echo ======================================================
echo Pack Complete!
echo  - %PARENT_DIR%\%FOLDER_NAME%.zip
echo ======================================================
pause
