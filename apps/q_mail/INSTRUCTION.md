# `q_mail` — Developer Instructions & Architecture Guide

## 1. Overview & Purpose
`q_mail` is the **PST & Email Communication Forensic Engine** of ForensiQ.
It provides:
1. **High-Performance PST Streaming:** Direct extraction of 50+ GB PST files powered by `pypff` (`libpff-python-windows`) without high memory overhead.
2. **Robust Task State Machine:** Ingestion lifecycle (`PENDING` -> `UPLOADING` -> `PROCESSING` -> `COMPLETED`, with `FAILED`, `CANCELLED`, and `STALLED` error recovery).
3. **Worker Liveness & Heartbeats:** Periodic timestamp updates (`last_heartbeat_at`) enabling automatic detection and one-click recovery of stalled ingestion threads after server reload.
4. **Graceful Cancellation & Resource Cleanup:** Clean mid-flight worker cancellation with partial evidence preservation and explicit `connection.close()` database connection leak prevention.
5. **Server-Side Data Grid:** Tabulator.js remote paginated grid with composite indexes across 500,000+ emails.

---

## 2. Strict Architectural Rules
* **4-Tier Architecture:** Maintain strict separation: `backend/pst_parser.py`, `models.py`, `selectors.py`, `services.py`, and `views.py`.
* **Zero N+1 Queries:** Always use `select_related` and `prefetch_related` in selectors.
* **Atomic Mutations:** All database writes and batch inserts must occur inside `@transaction.atomic` service methods.
* **Thread Connection Cleanup:** Any background worker thread must call `connection.close()` inside a `finally` block.
* **No Raw Hardcoded Strings or Fallbacks:** Follow `.env` zero-secret standards.

