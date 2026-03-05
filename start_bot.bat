@echo off
chcp 65001 >nul
echo ================================
echo   Qiosk2 - AI Asistan Bot
echo ================================
echo.

REM Python kontrolü
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python bulunamadı! Lütfen Python 3.10+ kurun.
    pause
    exit /b 1
)

REM .env kontrolü
if not exist ".env" (
    echo ❌ .env dosyası bulunamadı!
    echo.
    echo .env.example dosyasını .env olarak kopyalayıp düzenleyin:
    echo   copy .env.example .env
    echo.
    pause
    exit /b 1
)

REM Bağımlılıkları kur
echo 📦 Bağımlılıklar kontrol ediliyor...
pip install -r requirements.txt -q

echo.
echo 🤖 Bot başlatılıyor...
echo   Durdurmak için Ctrl+C
echo.
python main.py

pause
