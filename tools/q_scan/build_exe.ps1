<#
.SYNOPSIS
    Compiles ForensiQ Q-Scan into a standalone Windows .exe using Nuitka.
.DESCRIPTION
    Uses LTO (Link-Time Optimization) and anti-bloat optimizations for maximum raw NTFS file I/O speed.
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Compiling ForensiQ Q-Scan with Nuitka High-Performance Optimizations" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

$NuitkaArgs = @(
    "--standalone",
    "--onefile",
    "--lto=yes",
    "--enable-plugin=anti-bloat",
    "--assume-yes-for-downloads",
    "--windows-console-mode=force",
    "--output-dir=dist",
    "--output-filename=q_scan.exe",
    "q_scan.py"
)

python -m nuitka @NuitkaArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n============================================================================" -ForegroundColor Green
    Write-Host " [SUCCESS] Compilation complete! Output executable: dist\q_scan.exe" -ForegroundColor Green
    Write-Host " Copy 'dist\q_scan.exe' and 'config.json' to any auditor target machine." -ForegroundColor Green
    Write-Host "============================================================================`n" -ForegroundColor Green
} else {
    Write-Host "`n[ERROR] Nuitka compilation failed. Please verify MSVC/MinGW C compiler is installed.`n" -ForegroundColor Red
}
