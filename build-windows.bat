@echo off
:: Drama Reels — Windows Build Script
:: Jalankan script ini di PC Windows lo untuk build installer

echo ============================================
echo   Drama Reels — Windows Build
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    echo Download dari: https://www.python.org/downloads/
    echo Jangan lupa centang "Add Python to PATH"
    pause
    exit /b 1
)

:: Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip tidak ditemukan!
    pause
    exit /b 1
)

echo [1/7] Installing Python dependencies...
pip install flask==3.1.0 faster-whisper==1.1.0 imageio-ffmpeg requests yt-dlp pyinstaller --quiet

echo [2/7] Downloading ffmpeg...
if not exist "tools" mkdir tools
if not exist "tools\ffmpeg.exe" (
    echo Downloading ffmpeg... (this may take a minute)
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'ffmpeg.zip'"
    powershell -Command "Expand-Archive -Path 'ffmpeg.zip' -DestinationPath 'ffmpeg-temp' -Force"
    for /r "ffmpeg-temp" %%f in (ffmpeg.exe) do copy "%%f" "tools\ffmpeg.exe" >nul
    for /r "ffmpeg-temp" %%f in (ffprobe.exe) do copy "%%f" "tools\ffprobe.exe" >nul
    rmdir /s /q ffmpeg-temp >nul 2>&1
    del ffmpeg.zip >nul 2>&1
    echo ffmpeg downloaded!
) else (
    echo ffmpeg already exists, skipping.
)

echo [3/7] Downloading yt-dlp...
if not exist "tools\yt-dlp.exe" (
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' -OutFile 'tools\yt-dlp.exe'"
    echo yt-dlp downloaded!
) else (
    echo yt-dlp already exists, skipping.
)

echo [4/7] Generating icon...
python scripts\make_icon.py

echo [5/7] Building executable with PyInstaller...
pyinstaller drama-reels.spec --clean --noconfirm

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

echo [6/7] Creating LICENSE...
echo Drama Reels Pipeline > LICENSE.txt
echo Copyright (c) 2026 Archanist >> LICENSE.txt
echo MIT License >> LICENSE.txt

echo [7/7] Building installer...
:: Check if Inno Setup is installed
where iscc >nul 2>&1
if errorlevel 1 (
    echo.
    echo [!] Inno Setup not found. 
    echo Download from: https://jrsoftware.org/isinfo.php
    echo After install, add to PATH or run: iscc installer.iss
    echo.
    echo [OK] Portable EXE built at: dist\DramaReels.exe
    echo      You can run it directly!
    echo.
) else (
    iscc installer.iss
    echo.
    echo [OK] Installer built at: installer-output\DramaReels-Setup-2.0.0.exe
)

echo.
echo ============================================
echo   Build selesai!
echo.
echo   Portable: dist\DramaReels.exe
echo   Installer: installer-output\DramaReels-Setup-2.0.0.exe
echo.
echo   Jalankan DramaReels.exe, browser akan
echo   terbuka otomatis ke http://localhost:7860
echo ============================================
pause
