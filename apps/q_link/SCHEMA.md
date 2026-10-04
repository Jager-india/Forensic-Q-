# `q_link` — Database Schema & ERD Specifications

> [!TIP]
> **dbdiagram.io Compatibility:** Copy and paste the DBML code below directly into [dbdiagram.io](https://dbdiagram.io) to generate visual Entity-Relationship diagrams.

---

## 1. DBML (Database Markup Language for dbdiagram.io)

```dbml
// ==========================================
// Q-Link Forensic Graph & Intelligence Schema
// dbdiagram.io specification
// ==========================================

Table forensic_entities {
  id uuid [pk, default: `uuid4()`]
  entity_type varchar(32) [note: 'EMPLOYEE, VENDOR, CUSTOMER, COMPANY, BANK_ACCOUNT, EMAIL_ID, PHONE, PO, INVOICE, DOCUMENT']
  identifier varchar(255) [not null, unique, note: 'Normalized canonical identifier']
  display_name varchar(255) [not null]
  category varchar(64) [default: 'General']
  risk_rating int [default: 0]
  is_target boolean [default: false]
  metadata json
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

Table entity_aliases {
  id uuid [pk, default: `uuid4()`]
  entity_id uuid [ref: > forensic_entities.id]
  alias_name varchar(255) [not null, db_index]
  match_source varchar(64) [default: 'EXACT', note: 'EXACT, RAPIDFUZZ, LLM_INFERRED, MANUAL']
  confidence float [default: 1.0]
  created_at timestamp [default: `now()`]
}

Table entity_relationships {
  id uuid [pk, default: `uuid4()`]
  source_entity_id uuid [ref: > forensic_entities.id]
  target_entity_id uuid [ref: > forensic_entities.id]
  relation_type varchar(64) [note: 'EMAILED, TRANSFERRED_FUNDS, ISSUED_PO, APPROVED_BY, SHARED_IDENTIFIER, CONDUIT_TO, DIRECTOR_OF']
  confidence_score float [default: 1.0]
  weight float [default: 1.0]
  source_module varchar(32) [note: 'q_bank, q_trail, q_mail, q_ledger, q_verify, q_scan, q_voice']
  is_direct boolean [default: true]
  metadata json
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

Table evidence_pointers {
  id uuid [pk, default: `uuid4()`]
  relationship_id uuid [ref: > entity_relationships.id]
  source_module varchar(32) [not null]
  source_model varchar(64) [not null, note: 'BankTransaction, PurchaseOrder, EmailMessage, etc.']
  source_record_id varchar(128) [not null]
  evidence_url varchar(255) [not null, note: 'Direct route to original evidence']
  summary_snippet text
  occurred_at timestamp
  metadata json
  created_at timestamp [default: `now()`]
}

Table forensic_timeline_events {
  id uuid [pk, default: `uuid4()`]
  entity_id uuid [ref: > forensic_entities.id]
  relationship_id uuid [ref: > entity_relationships.id, null]
  event_title varchar(255) [not null]
  event_description text
  event_timestamp timestamp [not null]
  source_module varchar(32) [not null]
  severity varchar(16) [default: 'INFO']
  metadata json
  created_at timestamp [default: `now()`]
}

Table relationship_alerts {
  id uuid [pk, default: `uuid4()`]
  title varchar(255) [not null]
  alert_level varchar(16) [default: 'MEDIUM', note: 'LOW, MEDIUM, HIGH, CRITICAL']
  primary_entity_id uuid [ref: > forensic_entities.id]
  related_entities json [note: 'Array of entity UUIDs and names']
  risk_score int [default: 50]
  trigger_reason text
  ai_summary text [note: 'Synthesized narrative by LLM']
  is_acknowledged boolean [default: false]
  created_at timestamp [default: `now()`]
}
```

---

## 2. Django ORM Architecture
All models inherit from `core.models.ForensicBaseModel`, ensuring UUID primary keys and ISO timestamp telemetry.
