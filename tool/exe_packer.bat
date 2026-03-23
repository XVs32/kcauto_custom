@echo off
set "VENV_PATH=..\.venv"
set "BIN_PATH=..\bin"
set "ROOT_PATH=..\"
set "src=..\kcauto\__main__.py"

:: Activate the virtual environment
call "%VENV_PATH%\Scripts\activate.bat"

:: Get site-packages from the virtual environment
for /f "delims=" %%i in ('python -c "import site; print(site.getsitepackages()[0])"') do set "python_site_package=%%i"
echo The Python site-packages directory is: %python_site_package%

:: Build the first executable
if exist "%BIN_PATH%\kcauto_custom" rmdir /s /q "%BIN_PATH%\kcauto_custom"
python -m PyInstaller -D --clean %src% -p ..\kcauto\ -p %python_site_package% --distpath %BIN_PATH% --name "kcauto_custom"
rmdir /s /q ".\dist"
rmdir /s /q ".\build"
del .\__main__.spec
:: Create wrapper in project root
> "%ROOT_PATH%kcauto_custom.bat" echo @echo off
>> "%ROOT_PATH%kcauto_custom.bat" echo "%~dp0bin\kcauto_custom\kcauto_custom.exe" %%*

:: Build the second executable
set "src=..\kcauto\kcauto_cui.py"
if exist "%BIN_PATH%\kcauto_cui" rmdir /s /q "%BIN_PATH%\kcauto_cui"
python -m PyInstaller -D --clean %src% -p ..\kcauto\ -p %python_site_package% --distpath %BIN_PATH% --name "kcauto_cui"
rmdir /s /q ".\dist"
rmdir /s /q ".\build"
del .\kcauto_cui.spec
:: Create wrapper in project root
> "%ROOT_PATH%kcauto_cui.bat" echo @echo off
>> "%ROOT_PATH%kcauto_cui.bat" echo "%~dp0bin\kcauto_cui\kcauto_cui.exe" %%*

:: Deactivate the virtual environment
call "%VENV_PATH%\Scripts\deactivate.bat"

echo Build complete!
pause