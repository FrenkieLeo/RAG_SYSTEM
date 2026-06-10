@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher "py" was not found. Install Python 3.12+ to build the exe.
    exit /b 1
)

if not exist ".venv" (
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

pyinstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name PdfBatchLocker ^
    --collect-all pypdf ^
    pdf_batch_locker\__main__.py

echo.
echo Build complete: dist\PdfBatchLocker.exe
endlocal
