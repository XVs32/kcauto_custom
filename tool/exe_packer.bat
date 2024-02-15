@echo off

set "src=..\kcauto\__main__.py"
set "target_path=..\kcauto.exe"

for /f "delims=" %%i in ('python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())"') do set "python_site_package=%%i"

echo The Python site-packages directory is: %python_site_package%

python -m PyInstaller -F %src% -p ..\kcauto\ -p %python_site_package%
move /y ".\dist\__main__.exe" "%target_path%"
rmdir /s /q ".\dist"
rmdir /s /q ".\build"
del .\__main__.spec

set "src=..\kcauto\kcauto_cui.py"
set "target_path=..\kcauto_cui.exe"
python -m PyInstaller -F %src% -p ..\kcauto\ -p %python_site_package%
move /y ".\dist\kcauto_cui.exe" "%target_path%"
rmdir /s /q ".\dist"
rmdir /s /q ".\build"
del .\kcauto_cui.spec

pause