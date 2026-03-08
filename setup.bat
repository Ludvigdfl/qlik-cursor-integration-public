@echo off
cd /d "%~dp0"
pip install uv
uv sync
echo.
echo Setup complete. You can now use the qlik CLI.
pause
