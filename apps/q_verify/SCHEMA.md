# `q_verify` — Database Schema & ERD Specifications

> [!TIP]
> **dbdiagram.io Compatibility:** Copy and paste the DBML code below directly into [dbdiagram.io](https://dbdiagram.io) to generate visual Entity-Relationship diagrams.

---

## 1. DBML (Database Markup Language for dbdiagram.io)

```dbml
// ==========================================
// Q-Verify Document Authenticity & Forensic Schema
// dbdiagram.io specification
// ==========================================

Enum CaseStatus {
  PENDING
  PROCESSING
  COMPLETED
  FAILED
}

Enum RiskLevel {
  AUTHENTIC
  SUSPICIOUS
  HIGH_RISK_TAMPERED
}

Table verification_cases {
  id uuid [pk, default: `uuid4()`]
  case_ref varchar(64) [unique, not null, db_index: true, note: 'Case Reference e.g. VER-AUD-2026-001']
  case_title varchar(255) [not null]
  custodian_name varchar(255) [not null, note: 'Target Custodian / Auditee']
  custodian_email varchar(255) [default: '']
  custodian_department varchar(128) [default: '']
  notes text [default: '']
  status CaseStatus [default: 'PENDING', db_index: true]
  total_documents int [default: 0]
  authentic_count int [default: 0]
  suspicious_count int [default: 0]
  tampered_count int [default: 0]
  average_authenticity_score float [default: 100.0]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

Table verified_documents {
  id uuid [pk, default: `uuid4()`]
  case_id uuid [ref: > verification_cases.id, note: 'Optional case association']
  filename varchar(255) [not null]
  file_size_bytes bigint [default: 0]
  mime_type varchar(128) [not null, default: 'application/octet-stream']
  file_extension varchar(32) [default: '']
  sha256_hash varchar(64) [not null, db_index: true, note: 'Physical Evidence Hash']
  storage_path varchar(512) [default: '']
  file_created_at timestamp
  file_modified_at timestamp
  meta_created_at timestamp [db_index: true, note: 'Embedded PDF/Office/EXIF creation timestamp']
  meta_modified_at timestamp [note: 'Embedded PDF/Office/EXIF modification timestamp']
  meta_author varchar(255) [default: '']
  meta_creator varchar(255) [default: '']
  meta_producer varchar(255) [default: '']
  meta_software varchar(255) [default: '', note: 'e.g. Adobe Acrobat, Canva, Photoshop']
  meta_company varchar(255) [default: '']
  meta_title varchar(512) [default: '']
  meta_subject varchar(512) [default: '']
  incremental_updates_count int [default: 0, note: 'PDF appended trailer count']
  editing_time_minutes int [default: 0, note: 'Office total editing minutes']
  revision_number varchar(64) [default: '']
  authenticity_score int [default: 100, db_index: true, note: '0 = Tampered, 100 = Authentic']
  risk_level RiskLevel [default: 'AUTHENTIC', db_index: true]
  has_timestamp_anomaly boolean [default: false, db_index: true]
  has_software_anomaly boolean [default: false, db_index: true]
  has_structural_anomaly boolean [default: false, db_index: true]
  anomalies json [note: 'Array of detected anomaly flags with severity and penalties']
  raw_metadata json [note: 'Complete raw extracted metadata tree']
  summary text [default: '']
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}
```

---

## 2. Key Forensic Database Invariants
1. **Multi-Format Coverage:** Extracts metadata across PDF, Office OpenXML (DOCX, XLSX, PPTX), and Images (JPEG, PNG, TIFF).
2. **Dual-Mode Persistence:** Supports standalone rapid file inspections (`case_id = NULL`) and structured audit cases.
3. **Audit Trail:** Preserves exact SHA-256 evidence hashes and raw metadata trees for forensic courtroom reporting.

