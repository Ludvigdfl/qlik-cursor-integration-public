@echo off
cd /d "%~dp0"
py -m ensurepip --upgrade
pip install uv
uv sync
echo.
echo Setup complete. You can now use the qlik CLI.
pause
