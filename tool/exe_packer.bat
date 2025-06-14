@echo off
set "VENV_PATH=..\.venv"
set "src=..\kcauto\__main__.py"
set "target_path=..\kcauto.exe"

:: Activate the virtual environment
call "%VENV_PATH%\Scripts\activate.bat"

:: Get site-packages from the virtual environment
for /f "delims=" %%i in ('python -c "import site; print(site.getsitepackages()[0])"') do set "python_site_package=%%i"
echo The Python site-packages directory is: %python_site_package%

:: Build the first executable
python -m PyInstaller -F %src% -p ..\kcauto\ -p ..\pyvisauto\ -p %python_site_package%
move /y ".\dist\__main__.exe" "%target_path%"
rmdir /s /q ".\dist"
rmdir /s /q ".\build"
del .\__main__.spec

:: Build the second executable
set "src=..\kcauto\kcauto_cui.py"
set "target_path=..\kcauto_cui.exe"
python -m PyInstaller -F %src% -p ..\kcauto\ -p ..\pyvisauto\ -p %python_site_package%
move /y ".\dist\kcauto_cui.exe" "%target_path%"
rmdir /s /q ".\dist"
rmdir /s /q ".\build"
del .\kcauto_cui.spec

:: Deactivate the virtual environment
call "%VENV_PATH%\Scripts\deactivate.bat"

echo Build complete!
pause