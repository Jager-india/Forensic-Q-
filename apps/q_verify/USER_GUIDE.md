# `q_verify` — Investigator & Auditor User Guide

## 1. Investigative Workflow
1. **Rapid Standalone Inspection:** Drag and drop any suspicious invoice, contract, or image directly onto the Rapid Dropzone on the dashboard for instant timestamp & software analysis without creating a case.
2. **Case Creation & Batch Ingestion:** Click **"New Verification Case"** to create a dedicated investigation for a specific vendor or custodian, then drop 10+ documents simultaneously.
3. **Forensic Evidence Grid (Tabulator.js):**
   - Filter documents by Authenticity Score (`Authentic` &ge; 80, `Suspicious` 50-79, `Tampered` &lt; 50).
   - Search across filenames, authors, generators, and SHA-256 evidence hashes.
4. **Slide-Over Forensic Inspector:** Click any document row to view:
   - **Authenticity Score & Rationale:** Detailed summary of penalties and flags.
   - **Side-by-Side Timestamp Matrix:** Compare embedded creation, modification, and filesystem timestamps to catch backdating.
   - **Author & Generator Signatures:** Identify Canva, Photoshop, or online PDF converters used on formal corporate paperwork.
   - **PDF Structural Revisions:** Verify whether appended PDF revisions indicate post-signing modifications.
   - **Raw Metadata Dictionary:** Full technical property tree for courtroom-ready forensic reports.
   - **Evidence Download:** Direct access to original files.

