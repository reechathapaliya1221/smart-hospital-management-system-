@echo off
color 0A
title Smart Hospital Queue System Setup

echo ========================================
echo    Smart Hospital Queue System Setup
echo ========================================
echo.

REM Create necessary directories
echo Creating directories...
if not exist "logs" mkdir logs
if not exist "media" mkdir media
if not exist "media\qr_codes" mkdir media\qr_codes
if not exist "staticfiles" mkdir staticfiles
if not exist "ml_model" mkdir ml_model
if not exist "queue_system\templates\queue_system" mkdir queue_system\templates\queue_system
if not exist "static\css" mkdir static\css
if not exist "static\js" mkdir static\js
echo Directories created
echo.

REM Activate virtual environment
echo Activating virtual environment...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    python -m venv venv
    call venv\Scripts\activate.bat
)
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install compatible versions
echo Installing Django and dependencies...
pip uninstall django django-crispy-forms crispy-bootstrap5 -y
pip install django==5.2
pip install django-crispy-forms==2.3
pip install crispy-bootstrap5==0.7
pip install scikit-learn pandas numpy joblib
pip install channels channels-redis
pip install twilio djangorestframework
pip install pillow qrcode
echo.

REM Check if Django project exists
if not exist "manage.py" (
    echo Creating Django project...
    django-admin startproject hospital_queue .
    python manage.py startapp queue_system
)

REM Create basic __init__.py files
echo Creating __init__.py files...
if not exist "queue_system\__init__.py" echo # Queue System App > queue_system\__init__.py
if not exist "ml_model\__init__.py" echo # ML Model > ml_model\__init__.py
echo.

REM Run migrations
echo Running database migrations...
python manage.py makemigrations
python manage.py migrate
echo.

REM Create superuser
echo Creating admin superuser...
echo.
echo Please create admin account:
python manage.py createsuperuser
echo.

echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo To start the server:
echo   venv\Scripts\activate
echo   python manage.py runserver
echo.
echo Then open: http://127.0.0.1:8000
echo.
pause