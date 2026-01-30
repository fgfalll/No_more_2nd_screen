@echo off
echo Building No More 2nd Screen...
echo.

REM Activate venv
call .venv\Scripts\activate.bat

REM Run build
python build_exe.py

pause
