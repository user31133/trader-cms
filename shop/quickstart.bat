@echo off
echo 🚀 Shop Backend Quickstart
echo ==========================
echo.

REM Check if .env exists
if not exist .env (
    echo ❌ .env file not found!
    echo 📝 Creating .env from .env.example...
    copy .env.example .env
    echo ✅ .env created. Please edit it with your configuration.
    echo.
    echo Required configuration:
    echo   - DATABASE_URL: PostgreSQL connection string
    echo   - ADMIN_API_BASE_URL: Main backend API URL
    echo   - TRADER_ID: Trader ID for this shop instance
    echo   - JWT_SECRET_KEY: Secret for JWT tokens
    echo   - SESSION_SECRET_KEY: Secret for sessions
    echo.
    pause
)

REM Check if virtual environment exists
if not exist venv (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

echo.
echo ✅ Setup complete!
echo.
echo Next steps:
echo 1. Run migrations from trader-cms:
echo    cd ..\trader-cms ^&^& alembic upgrade head
echo.
echo 2. Start the shop server:
echo    uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
echo.
echo 3. Access API docs at:
echo    http://localhost:8001/api/docs
echo.
pause
