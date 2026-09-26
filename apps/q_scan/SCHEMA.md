# `q_scan` — Database Schema & ERD Specifications

> [!TIP]
> **dbdiagram.io Compatibility:** Copy and paste the DBML code below directly into [dbdiagram.io](https://dbdiagram.io) to generate visual Entity-Relationship diagrams.

---

## 1. DBML (Database Markup Language for dbdiagram.io)

```dbml
// ==========================================
// Q-Scan Endpoint Drive & File Forensics Schema
// dbdiagram.io specification
// ==========================================

Table scanned_devices {
  id uuid [pk, default: `uuid4()`]
  hostname varchar(128) [not null]
  scan_title varchar(255)
  custodian_name varchar(255)
  drive_letter varchar(64)
  file_system varchar(32)
  status varchar(32) [default: 'IMPORTED']
  total_files_scanned int [default: 0]
  total_matches_found int [default: 0]
  total_bytes_scanned bigint [default: 0]
  scan_completed_at timestamp
  notes text
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

Table file_evidence_hits {
  id uuid [pk, default: `uuid4()`]
  device_id uuid [ref: > scanned_devices.id]
  file_path varchar(1024) [not null]
  filename varchar(255) [not null]
  extension varchar(32)
  file_size_bytes bigint [not null, default: 0]
  matched_keyword varchar(128) [not null]
  match_type varchar(64) [default: 'CONTENT_TEXT']
  snippet text
  file_modified_at timestamp
  detection_timestamp timestamp
  risk_score int [default: 50]
  is_reviewed boolean [default: false]
  reviewer_notes text
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}
```

---

## 2. Django ORM Models

```python
from django.db import models
from core.models import ForensicBaseModel


class ScannedDevice(ForensicBaseModel):
    hostname = models.CharField(max_length=128, db_index=True)
    scan_title = models.CharField(max_length=255, blank=True, default="")
    custodian_name = models.CharField(max_length=255, blank=True, default="")
    drive_letter = models.CharField(max_length=64, blank=True, default="")
    file_system = models.CharField(max_length=32, blank=True, default="")
    status = models.CharField(max_length=32, default="IMPORTED", db_index=True)
    total_files_scanned = models.IntegerField(default=0)
    total_matches_found = models.IntegerField(default=0)
    total_bytes_scanned = models.BigIntegerField(default=0)
    scan_completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")


class FileEvidenceHit(ForensicBaseModel):
    device = models.ForeignKey(ScannedDevice, on_delete=models.CASCADE, related_name="hits")
    file_path = models.CharField(max_length=1024, db_index=True)
    filename = models.CharField(max_length=255, db_index=True)
    extension = models.CharField(max_length=32, blank=True, default="", db_index=True)
    file_size_bytes = models.BigIntegerField(default=0)
    matched_keyword = models.CharField(max_length=128, db_index=True)
    match_type = models.CharField(max_length=64, default="CONTENT_TEXT", db_index=True)
    snippet = models.TextField(blank=True, default="")
    file_modified_at = models.DateTimeField(null=True, blank=True)
    detection_timestamp = models.DateTimeField(null=True, blank=True)
    risk_score = models.IntegerField(default=50)
    is_reviewed = models.BooleanField(default=False)
    reviewer_notes = models.TextField(blank=True, default="")
```
