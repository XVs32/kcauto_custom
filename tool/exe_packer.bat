@echo off
:: Force UTF-8 encoding in cmd and Python output
chcp 65001 >nul
set PYTHONUTF8=1

:: Paths
set "VENV_PATH=..\.venv"
set "src=..\kcauto\__main__.py"
set "target_path=..\kcauto_custom.exe"

:: Activate the virtual environment
call "%VENV_PATH%\Scripts\activate.bat"

:: Get site-packages path from venv
for /f "delims=" %%i in ('python -c "import site; print(site.getsitepackages()[0])"') do set "python_site_package=%%i"
echo The Python site-packages directory is: %python_site_package%

:: === Build first executable: __main__.py ===
python -m PyInstaller -F %src% -p ..\kcauto\ -p ..\pyvisauto\ -p %python_site_package%
move /y ".\dist\__main__.exe" "%target_path%"
rmdir /s /q ".\dist"
rmdir /s /q ".\build"
del /q .\__main__.spec

:: === Build second executable: kcauto_cui.py ===
set "src=..\kcauto\kcauto_cui.py"
set "target_path=..\kcauto_cui.exe"
python -m PyInstaller -F %src% -p ..\kcauto\ -p ..\pyvisauto\ -p %python_site_package%
move /y ".\dist\kcauto_cui.exe" "%target_path%"
rmdir /s /q ".\dist"
rmdir /s /q ".\build"
del /q .\kcauto_cui.spec

:: Deactivate virtual environment
call "%VENV_PATH%\Scripts\deactivate.bat"

echo Build complete!
pause