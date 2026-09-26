@echo off
REM ============================================================================
REM ForensiQ Q-Scan: Standalone Windows .exe Compiler Script (Nuitka)
REM ============================================================================
REM Compiles tools/q_scan/q_scan.py into a single, high-performance binary.
REM ============================================================================

echo ============================================================================
echo   Compiling ForensiQ Q-Scan with Nuitka High-Performance Optimizations
echo ============================================================================

cd /d "%~dp0"

python -m nuitka ^
    --standalone ^
    --onefile ^
    --lto=yes ^
    --enable-plugin=anti-bloat ^
    --assume-yes-for-downloads ^
    --windows-console-mode=force ^
    --output-dir=dist ^
    --output-filename=q_scan.exe ^
    q_scan.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================================
    echo [SUCCESS] Compilation complete! Output executable: dist\q_scan.exe
    echo Copy 'dist\q_scan.exe' and 'config.json' to any auditor target machine.
    echo ============================================================================
) else (
    echo.
    echo [ERROR] Nuitka compilation failed. Please verify Nuitka and C compiler (MSVC/MinGW) are installed.
)

pause
