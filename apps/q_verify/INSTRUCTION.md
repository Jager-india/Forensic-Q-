# `q_verify` — Developer Instructions & Architecture Guide

## 1. Overview & Purpose
`q_verify` is the **Document Authenticity & Metadata Forensic Engine** of ForensiQ.
It provides:
1. **Multi-Format Forensic Inspection:** Direct metadata extraction across PDF (`pypdf`), Office OpenXML DOCX/XLSX/PPTX (`zipfile` & `xml`), and Images (`Pillow` EXIF/XMP).
2. **Timestamp Discrepancy Auditing:** Compares internal creation & modification timestamps vs filesystem dates to detect backdated contracts and post-facto edits.
3. **PDF Structural & Incremental Update Analysis:** Detects appended `%%EOF` trailers, cross-reference overwrites, and post-generation text/signature alterations.
4. **Software Generator Profiling:** Identifies suspect image manipulation tools (Photoshop, Canva, GIMP, Snapseed) and consumer online PDF editors (iLovePDF, Smallpdf, Sejda).
5. **0-100 Authenticity Scoring:** Calculates a weighted forensic integrity score categorizing files into `AUTHENTIC`, `SUSPICIOUS`, and `HIGH_RISK_TAMPERED`.

---

## 2. Strict Architectural Rules
* **4-Tier Architecture:** Maintain clean separation: `backend/`, `models.py`, `selectors.py`, `services.py`, and `views.py`.
* **Zero Dummy Fallbacks:** Run authentic forensic analysis on binary streams without mock dictionaries.
* **Proactive N+1 Prevention:** Use `select_related("case")` and server-side Tabulator.js pagination.
* **Cotton & UI Standard:** Use rose accent tokens (`bg-rose-600`, `text-rose-400`), stat cards, and slide-over reader drawers.

