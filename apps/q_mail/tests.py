import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import MailboxInvestigation


class QMailUploadAndIngestionTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Set portal session auth so middleware permits access
        session = self.client.session
        session["portal_authenticated"] = True
        session.save()

    @patch("q_mail.views.start_mailbox_processing")
    def test_initiate_upload_and_chunked_streaming(self, mock_start_processing):
        # 1. Test initiating upload
        init_url = reverse("q_mail:upload_initiate")
        payload = {
            "audit_ref": "AUD-TEST-2026-001",
            "audit_name": "Test Forensic Audit",
            "auditee_name": "John Doe",
            "auditee_email": "john.doe@enterprise.internal",
            "auditee_department": "Finance",
            "auditee_designation": "Director",
            "pst_file_name": "sample_evidence.pst",
            "file_size_bytes": 3000,
        }
        res = self.client.post(
            init_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        mailbox_id = data["mailbox_id"]

        # Verify DB object
        inv = MailboxInvestigation.objects.get(id=mailbox_id)
        self.assertEqual(inv.audit_ref, "AUD-TEST-2026-001")
        self.assertEqual(inv.auditee_name, "John Doe")

        # 2. Test uploading file in 3 binary chunks
        chunk_url = reverse("q_mail:upload_chunk")
        full_content = b"PST_HEADER_DUMMY_BINARY_DATA_" * 100
        expected_sha256 = hashlib.sha256(full_content).hexdigest()

        chunk_size = len(full_content) // 3
        chunks = [
            full_content[:chunk_size],
            full_content[chunk_size : chunk_size * 2],
            full_content[chunk_size * 2 :],
        ]

        for idx, chunk_bytes in enumerate(chunks):
            chunk_file = SimpleUploadedFile(
                f"chunk_{idx}.bin", chunk_bytes, content_type="application/octet-stream"
            )
            chunk_res = self.client.post(
                chunk_url,
                data={
                    "mailbox_id": mailbox_id,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "chunk": chunk_file,
                },
            )
            self.assertEqual(chunk_res.status_code, 200)
            chunk_data = chunk_res.json()
            self.assertTrue(chunk_data["success"])

            if idx == len(chunks) - 1:
                self.assertTrue(chunk_data["is_completed"])
                self.assertEqual(chunk_data["file_sha256"], expected_sha256)

        # 3. Verify file on disk
        inv.refresh_from_db()
        expected_path = Path(settings.MEDIA_ROOT) / "uploads" / "pst" / f"{mailbox_id}.pst"
        self.assertTrue(expected_path.exists())
        self.assertEqual(inv.file_sha256, expected_sha256)
        self.assertEqual(inv.file_size_bytes, len(full_content))

        # 4. Test progress API
        progress_url = reverse("q_mail:progress_api", kwargs={"mailbox_id": mailbox_id})
        prog_res = self.client.get(progress_url)
        self.assertEqual(prog_res.status_code, 200)
        self.assertEqual(prog_res.json()["audit_ref"], "AUD-TEST-2026-001")

        # 5. Test paginated messages API
        messages_url = reverse("q_mail:messages_api", kwargs={"mailbox_id": mailbox_id})
        msg_res = self.client.get(messages_url)
        self.assertEqual(msg_res.status_code, 200)
        self.assertIn("data", msg_res.json())
        self.assertIn("last_page", msg_res.json())

        # Cleanup test upload file
        if expected_path.exists():
            expected_path.unlink()

    def test_cancellation_flow(self):
        inv = MailboxInvestigation.objects.create(
            audit_ref="AUD-CANCEL-001",
            audit_name="Cancellation Test",
            auditee_name="Jane Doe",
            auditee_email="jane.doe@enterprise.internal",
            status=MailboxInvestigation.IngestionStatus.PROCESSING,
        )

        cancel_url = reverse("q_mail:cancel_process", kwargs={"mailbox_id": inv.id})
        res = self.client.post(cancel_url)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        inv.refresh_from_db()
        self.assertTrue(inv.is_cancellation_requested)

        # Check progress API returns cancellation flag
        prog_url = reverse("q_mail:progress_api", kwargs={"mailbox_id": inv.id})
        prog_res = self.client.get(prog_url)
        self.assertEqual(prog_res.status_code, 200)
        self.assertTrue(prog_res.json()["is_cancellation_requested"])

    def test_stalled_investigation_recovery(self):
        from datetime import UTC, datetime, timedelta

        from .services import recover_stalled_investigations

        # 1. Stalled investigation (heartbeat 10 minutes ago)
        stalled_inv = MailboxInvestigation.objects.create(
            audit_ref="AUD-STALL-001",
            audit_name="Stall Test",
            auditee_name="Stalled User",
            auditee_email="stalled@enterprise.internal",
            status=MailboxInvestigation.IngestionStatus.PROCESSING,
            last_heartbeat_at=datetime.now(UTC) - timedelta(minutes=10),
        )

        # 2. Healthy active investigation (heartbeat 5 seconds ago)
        active_inv = MailboxInvestigation.objects.create(
            audit_ref="AUD-ACTIVE-002",
            audit_name="Active Test",
            auditee_name="Active User",
            auditee_email="active@enterprise.internal",
            status=MailboxInvestigation.IngestionStatus.PROCESSING,
            last_heartbeat_at=datetime.now(UTC) - timedelta(seconds=5),
        )

        # Run recovery
        recovered_count = recover_stalled_investigations(stale_seconds=180)
        self.assertEqual(recovered_count, 1)

        stalled_inv.refresh_from_db()
        active_inv.refresh_from_db()

        self.assertEqual(stalled_inv.status, MailboxInvestigation.IngestionStatus.STALLED)
        self.assertIn("interrupted", stalled_inv.error_message)
        self.assertEqual(active_inv.status, MailboxInvestigation.IngestionStatus.PROCESSING)

    def test_restart_resumes_stalled_investigation(self):
        inv = MailboxInvestigation.objects.create(
            audit_ref="AUD-RESUME-001",
            audit_name="Resume Test",
            auditee_name="Resume User",
            auditee_email="resume@enterprise.internal",
            status=MailboxInvestigation.IngestionStatus.STALLED,
            error_message="Previous crash",
            is_cancellation_requested=True,
        )

        # Trigger restart
        process_url = reverse("q_mail:trigger_process", kwargs={"mailbox_id": inv.id})
        res = self.client.post(process_url)
        self.assertEqual(res.status_code, 200)

        inv.refresh_from_db()
        self.assertEqual(inv.status, MailboxInvestigation.IngestionStatus.PROCESSING)
        self.assertFalse(inv.is_cancellation_requested)
        self.assertEqual(inv.error_message, "")
