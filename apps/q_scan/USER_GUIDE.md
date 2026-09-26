# `q_scan` — Investigator & Field Auditor User Guide

## 1. Overview
Q-Scan is a forensic endpoint filesystem scanner designed for rapid enterprise investigations, employee departure audits, and discovery triage.

---

## 2. Field Auditor Deployment Workflow (Offline Machine)

### Option A: Standalone Single Executable (`q_scan.exe`)
1. Copy `q_scan.exe` and `config.json` onto an external USB drive.
2. Plug into the target workstation.
3. Edit `config.json` if you wish to adjust target directories, keywords, or exclusions.
4. Double-click `q_scan.exe` (or run in PowerShell as Administrator for protected drive access).
5. The scanner traverses all target drives at native NTFS speed, displaying a live console progress bar.
6. Every match is written immediately with `os.fsync()` to `scan_results.csv` on the root execution directory.
7. If interrupted with `Ctrl+C`, zero evidence is lost.

### Option B: Compilation via Nuitka
To compile the standalone Windows binary yourself from source:
```bash
uv run nuitka --standalone --onefile --assume-yes-for-downloads --output-filename=q_scan.exe tools/q_scan/q_scan.py
```

---

## 3. Central Web Dashboard Evidence Ingestion

1. Navigate to the ForensiQ portal at `http://127.0.0.1:8000/scan/`.
2. Click **Import Scan Results CSV**.
3. Enter the Hostname (e.g. `CFO-LAPTOP-01`), Custodian, and Investigation Label.
4. Select the `scan_results.csv` file and click **Parse & Ingest Findings**.
5. The evidence engine automatically parses match types, calculates risk scores (10-99), and extracts surrounding context snippets.
6. Use the interactive Tabulator data grid to filter by risk level, match type, or keyword, and export reports to CSV or JSON.
