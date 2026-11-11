@echo off
rem Cria o ambiente Python da skill em <base>\venv (numpy + Pillow + SciPy).
rem <base> = a pasta que contém skills\ (D:\FerramentasMinecraft no PC, C:\FerramentasMinecraft no notebook).
for %%I in ("%~dp0..\..") do set "BASE=%%~fI"
set "PIP_CACHE_DIR=%BASE%\.pip-cache"
set "TEMP=%BASE%\.tmp"
set "TMP=%BASE%\.tmp"
if not exist "%TEMP%" mkdir "%TEMP%"
if not exist "%BASE%\venv\Scripts\python.exe" python -m venv "%BASE%\venv"
"%BASE%\venv\Scripts\python.exe" -m pip install --upgrade pip
"%BASE%\venv\Scripts\python.exe" -m pip install numpy pillow scipy
echo.
echo Pronto. Python da skill: %BASE%\venv\Scripts\python.exe
pause
