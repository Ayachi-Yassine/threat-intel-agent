@echo off
REM One-time setup: creates venv, installs deps, copies .env template.
REM Run this once from the project root: scripts\setup.bat

python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo Created .env from template — edit it with your real API keys and passwords.
) else (
    echo .env already exists, leaving it as-is.
)

echo.
echo Setup done. Next steps:
echo   1. Edit .env with your GROQ_API_KEY, NEO4J_PASSWORD, etc.
echo   2. Run: venv\Scripts\activate
echo   3. Run: python -m tests.test_local
