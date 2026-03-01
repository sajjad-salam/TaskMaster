@echo off
REM ============================================
REM TaskMaster Build Script - Single EXE
REM بناء برنامج TaskMaster - ملف واحد
REM ============================================

echo.
echo ========================================
echo    TaskMaster Build Script
echo    سكريبت بناء برنامج TaskMaster
echo ========================================
echo.

REM Step 1: Clean previous builds
echo [1/3] Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "installer_output" rmdir /s /q "installer_output"
echo Cleaned!
echo.

REM Step 2: Build with PyInstaller (Single EXE Mode)
echo [2/3] Building with PyInstaller (Single EXE Mode)...
echo This may take a few minutes...
pyinstaller --clean TaskMaster.spec --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: PyInstaller build failed!
    echo خطأ: فشل بناء PyInstaller!
    pause
    exit /b 1
)
echo PyInstaller build completed!
echo.

REM Step 3: Create installer with Inno Setup
echo [3/3] Creating installer with Inno Setup...
echo.

REM Check if Inno Setup compiler exists
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "TaskMaster_setup.iss"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    "C:\Program Files\Inno Setup 6\ISCC.exe" "TaskMaster_setup.iss"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    "%ProgramFiles%\Inno Setup 6\ISCC.exe" "TaskMaster_setup.iss"
) else (
    echo WARNING: Inno Setup compiler not found!
    echo تحذير: لم يتم العثور على برنامج Inno Setup!
    echo.
    echo Please install Inno Setup from: https://jrsoftware.org/isdl.php
    echo أو تأكد من أن Inno Setup مثبت بشكل صحيح
    echo.
    echo The PyInstaller build is in: dist\TaskMaster.exe
    echo البناء موجود في: dist\TaskMaster.exe
    pause
    exit /b 0
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Inno Setup build failed!
    echo خطأ: فشل بناء Inno Setup!
    pause
    exit /b 1
)

echo.
echo ========================================
echo    BUILD COMPLETED SUCCESSFULLY!
echo    تم البناء بنجاح!
echo ========================================
echo.
echo Single EXE: dist\TaskMaster.exe
echo Installer: installer_output\TaskMaster_Setup_*.exe
echo.
pause
