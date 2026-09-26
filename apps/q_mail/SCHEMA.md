# `q_mail` — Database Schema & ERD Specifications

> [!TIP]
> **dbdiagram.io Compatibility:** Copy and paste the DBML code below directly into [dbdiagram.io](https://dbdiagram.io) to generate visual Entity-Relationship diagrams.

---

## 1. DBML (Database Markup Language for dbdiagram.io)

```dbml
// ==========================================
// Q-Mail Communication Forensics Schema
// dbdiagram.io specification
// ==========================================

Enum IngestionStatus {
  PENDING
  UPLOADING
  PROCESSING
  COMPLETED
  FAILED
  CANCELLED
  STALLED
}

Table mailbox_investigations {
  id uuid [pk, default: `uuid4()`]
  audit_ref varchar(64) [not null, db_index: true, note: 'Audit Case Number']
  audit_name varchar(255) [not null]
  auditee_name varchar(255) [not null, note: 'Target Custodian Name']
  auditee_email varchar(255) [not null]
  auditee_department varchar(128) [default: '']
  auditee_designation varchar(128) [default: '']
  pst_file_name varchar(255) [not null]
  pst_file_path varchar(512) [default: '']
  file_size_bytes bigint [default: 0]
  file_sha256 varchar(64) [default: '', note: 'Chain of Custody Evidence Hash']
  status IngestionStatus [default: 'PENDING', db_index: true]
  progress_percent float [default: 0.0]
  current_folder varchar(255) [default: '']
  total_messages_estimated int [default: 0]
  processed_messages_count int [default: 0]
  attachment_count int [default: 0]
  error_message text [default: '']
  processing_started_at timestamp
  processing_completed_at timestamp
  last_heartbeat_at timestamp [db_index: true]
  is_cancellation_requested boolean [default: false, db_index: true]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

Table email_messages {
  id uuid [pk, default: `uuid4()`]
  mailbox_id uuid [ref: > mailbox_investigations.id, not null]
  message_id varchar(255) [db_index: true]
  subject text [default: '(No Subject)']
  sender_name varchar(255) [default: '']
  sender_email varchar(255) [db_index: true]
  recipients_to json [note: 'List of To recipient strings']
  recipients_cc json [note: 'List of CC recipient strings']
  recipients_bcc json [note: 'List of BCC recipient strings']
  sent_date timestamp [db_index: true]
  delivery_date timestamp
  folder_path varchar(512) [db_index: true]
  body_plain text [default: '']
  body_html text [default: '']
  importance int [default: 1]
  conversation_topic varchar(512) [default: '']
  has_attachments boolean [default: false, db_index: true]
  attachment_count int [default: 0]
  matched_keywords json
  risk_score int [default: 0, db_index: true]
  risk_level varchar(16) [default: 'Low']
  is_flagged boolean [default: false, db_index: true]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

Table email_attachments {
  id uuid [pk, default: `uuid4()`]
  email_id uuid [ref: > email_messages.id, not null]
  filename varchar(255) [not null]
  file_size_bytes bigint [default: 0]
  mime_type varchar(128) [default: 'application/octet-stream']
  file_extension varchar(32) [default: '']
  sha256_hash varchar(64) [db_index: true, note: 'Physical Evidence Hash']
  storage_path varchar(512) [default: '']
  is_suspicious boolean [default: false, db_index: true]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

Table email_participants {
  id uuid [pk, default: `uuid4()`]
  mailbox_id uuid [ref: > mailbox_investigations.id, not null]
  email_address varchar(255) [db_index: true]
  display_name varchar(255) [default: '']
  sent_count int [default: 0]
  received_count int [default: 0]
  first_interaction timestamp
  last_interaction timestamp
  is_external_domain boolean [default: false]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}
```

---

## 2. Key Forensic Database Invariants
1. **Zero Data Loss on Cancellation:** Workers flush partial message batches atomically before marking status as `CANCELLED`.
2. **Heartbeat Liveness Tracking:** `last_heartbeat_at` is updated at every folder and batch iteration. Tasks inactive for >180s automatically transition to `STALLED`.
3. **Database Portability:** Fully compatible with both SQLite3 (WAL mode) for local dev and MSSQL for enterprise production.

