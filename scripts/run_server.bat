@echo off
REM Starts the webhook server. Run scripts\setup.bat first if you haven't.
call venv\Scripts\activate.bat
python -m app.main
