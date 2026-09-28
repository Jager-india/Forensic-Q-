# `q_mail` — Investigator & Auditor User Guide

## 1. Investigative Workflow
1. **Case Registration & PST Ingestion:** Click **"Ingest PST Mailbox (~50 GB)"** from the dashboard, fill in the custodian details (Name, Email, Department, Title) and drag-and-drop the `.pst` archive.
2. **Streaming Upload & Progress Tracking:** The upload portal uses 20 MB binary chunking to reliably stream files up to 50+ GB without HTTP payload limits. Live progress and extraction metrics are visible in real-time.
3. **Ingestion Controls & Resiliency:**
   - **Cancel Ingestion:** If an incorrect PST is uploaded, click **"Cancel Ingestion"** to safely terminate the background worker without data corruption. All already extracted emails are preserved.
   - **Resume / Retry:** If the server is restarted or interrupted, the task is marked **"Stalled"** or **"Cancelled"**. Click **"Resume Ingestion"** to restart extraction seamlessly.
4. **Forensic Evidence Grid (Tabulator.js):** Search subjects, senders, and body content with debounced live search and sort columns remotely.
5. **Slide-Over Forensic Reader:** Click any row to view message headers, extracted HTML/plain text, and download physical evidence attachments with verified SHA-256 hashes.
6. **Communication Counterparty Matrix:** Analyze top email contacts and external domain interactions visualized in the Plotly chart.
7. **Forensic Checkpoints Engine:** Inspect 10 critical audit flags (Currency/Monetary mentions, Without CC/BCC covert comms, Personal webmail senders, Apart from HMIL external domains, Primary bank statements & alerts, UPI transaction notifications, Default keywords: PAYMENT/GIFT/SALARY/TAX/LOAN/CIBIL, Participant search, and Date range filtering) with live KPI counters, instant filtering, badge flags, and one-click Excel evidence export.

