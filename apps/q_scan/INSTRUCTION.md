# `q_scan` — Developer Instructions & Architecture Guide

## 1. Overview & Purpose
`q_scan` is the **Endpoint Filesystem & Keyword Forensic Engine** of ForensiQ.
It delivers a hybrid architecture designed for enterprise investigations:
1. **Standalone Endpoint Scanner (`q_scan.exe` / `q_scan.py`):**
   - High-speed, non-recursive stack traversal via `os.scandir()`.
   - Windows Long Path (`\\?\`) handling to bypass the 260-character MAX_PATH limit.
   - Zero-buffer streaming CSV output with physical disk `os.fsync()` after every match.
   - Deep inspection of Office packages (`.docx`, `.xlsx`, `.pptx`) and `.zip` archives using pure Python standard library.
   - Zero external pip dependencies, compiled into a standalone Windows binary via Nuitka.
2. **Centralized Forensic Web Dashboard:**
   - Multi-endpoint evidence correlation, upload of `scan_results.csv`, risk scoring, and Tabulator.js data tables.

---

## 2. Directory Structure & Layers

```
apps/q_scan/
├── backend/
│   ├── __init__.py
│   └── disk_scanner.py     # HighPerformanceDiskScanner engine
├── migrations/
│   └── 0001_initial.py     # DB migrations
├── models.py               # ScannedDevice & FileEvidenceHit
├── selectors.py            # Read-only N+1 safe queries
├── services.py             # Atomic CSV ingestion and risk classification
├── views.py                # Thin presentation controllers
├── urls.py                 # URL routing (/scan/...)
├── templates/q_scan/       # Glassmorphic UI templates (Cotton components)
├── tests.py                # Comprehensive test suite
├── INSTRUCTION.md          # Architecture guide
├── SCHEMA.md               # DBML schema & model spec
└── USER_GUIDE.md           # Field auditor execution manual
```

---

## 3. Strict Rules & Architectural Constraints

- **Inherit Models from `core.models.ForensicBaseModel`:** Guarantees UUID v4 primary keys and automatic timestamp tracking.
- **Zero External Dependencies in Standalone Scanner:** `tools/q_scan/q_scan.py` must only use Python standard libraries (`os`, `sys`, `json`, `csv`, `time`, `pathlib`, `zipfile`, `re`).
- **Immediate Disk Persistence:** Never buffer CSV writes in memory; call `flush()` and `os.fsync()` on every match.
- **Stack-based Traversal:** Do not use `os.walk()` or recursive function calls; use an explicit `list.pop()` stack with `os.scandir()`.
- **Cotton Slots Syntax:** Always use `<c-slot name="...">` (never `<c-slot:name>`).
