import csv
import tempfile
import zipfile
from pathlib import Path

from django.test import Client, TestCase
from django.urls import reverse

from .backend.disk_scanner import HighPerformanceDiskScanner, load_or_create_config
from .models import FileEvidenceHit, ScannedDevice
from .selectors import (
    get_scan_dashboard_metrics,
)
from .services import delete_scanned_device, ingest_scan_csv_file


class HighPerformanceDiskScannerTests(TestCase):
    """
    Test suite for Q-Scan filesystem scanner and deep document/archive extraction engine.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.temp_dir.name)
        self.output_csv = self.root_path / "test_results.csv"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_filename_match(self):
        # Create file with keyword in filename
        target_file = self.root_path / "employee_password_list.txt"
        target_file.write_text("Regular content here", encoding="utf-8")

        scanner = HighPerformanceDiskScanner(
            target_directories=[str(self.root_path)],
            keywords=["password"],
            search_contents=False,
            output_csv_path=self.output_csv,
        )
        stats = scanner.run_scan()

        self.assertEqual(stats["matches_found"], 1)
        self.assertTrue(self.output_csv.exists())

        with open(self.output_csv, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
            self.assertEqual(len(rows), 2)  # Header + 1 match row
            self.assertEqual(rows[1][2], "password")
            self.assertEqual(rows[1][3], "FILENAME")

    def test_content_boundary_split_match(self):
        # Test boundary overlap buffer by splitting keyword across 64-byte chunks
        chunk_size = 64
        secret_keyword = "confidential_audit_token"
        pad_len = chunk_size - 10
        content = ("A" * pad_len) + secret_keyword + ("B" * 50)

        test_file = self.root_path / "stream_data.log"
        test_file.write_text(content, encoding="utf-8")

        scanner = HighPerformanceDiskScanner(
            target_directories=[str(self.root_path)],
            keywords=[secret_keyword],
            search_contents=True,
            chunk_size_bytes=chunk_size,
            output_csv_path=self.output_csv,
        )
        stats = scanner.run_scan()

        self.assertEqual(stats["matches_found"], 1)
        with open(self.output_csv, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1][2], secret_keyword)
            self.assertEqual(rows[1][3], "CONTENT_TEXT")
            self.assertIn("confidential_audit_token", rows[1][6])

    def test_deep_docx_inspection(self):
        # Create a mock .docx archive (zip with word/document.xml)
        docx_file = self.root_path / "report.docx"
        mock_doc_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:body>
                <w:p><w:r><w:t>Confidential kickback settlement agreement</w:t></w:r></w:p>
            </w:body>
        </w:document>"""

        with zipfile.ZipFile(docx_file, "w") as z:
            z.writestr("word/document.xml", mock_doc_xml)

        scanner = HighPerformanceDiskScanner(
            target_directories=[str(self.root_path)],
            keywords=["kickback"],
            search_contents=True,
            output_csv_path=self.output_csv,
        )
        stats = scanner.run_scan()

        self.assertEqual(stats["matches_found"], 1)
        with open(self.output_csv, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
            self.assertEqual(rows[1][2], "kickback")
            self.assertEqual(rows[1][3], "CONTENT_DOCX")

    def test_deep_zip_inspection(self):
        # Create a mock .zip containing an inner secret text file
        zip_file = self.root_path / "backup.zip"
        with zipfile.ZipFile(zip_file, "w") as z:
            z.writestr("notes/offshore_accounts.txt", "Bank balance in Panama: $5,000,000")

        scanner = HighPerformanceDiskScanner(
            target_directories=[str(self.root_path)],
            keywords=["offshore"],
            search_contents=True,
            output_csv_path=self.output_csv,
        )
        stats = scanner.run_scan()

        self.assertGreaterEqual(stats["matches_found"], 1)
        with open(self.output_csv, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
            self.assertEqual(rows[1][2], "offshore")

    def test_directory_and_extension_exclusions(self):
        # Excluded folder
        excluded_dir = self.root_path / ".git" / "logs"
        excluded_dir.mkdir(parents=True)
        (excluded_dir / "secret.txt").write_text("password=123", encoding="utf-8")

        # Excluded extension
        (self.root_path / "library.dll").write_text("password=123", encoding="utf-8")

        scanner = HighPerformanceDiskScanner(
            target_directories=[str(self.root_path)],
            keywords=["password"],
            exclude_directories=[str(self.root_path / ".git")],
            exclude_extensions=[".dll"],
            output_csv_path=self.output_csv,
        )
        stats = scanner.run_scan()

        self.assertEqual(stats["matches_found"], 0)

    def test_config_loader(self):
        cfg_path = self.root_path / "config.json"
        created_cfg = load_or_create_config(cfg_path)
        self.assertTrue(cfg_path.exists())
        self.assertIn("keywords", created_cfg)
        self.assertIn("exclude_directories", created_cfg)


class QScanDjangoServiceAndViewsTests(TestCase):
    """
    Test suite for Q-Scan Django services, selectors, and views.
    """

    def setUp(self):
        self.client = Client()
        # Authenticate session
        session = self.client.session
        session["portal_authenticated"] = True
        session.save()

    def test_csv_ingestion_service(self):
        csv_data = """Timestamp,File Path,Matched Keyword,Match Type,File Size (Bytes),Last Modified Date,Matching Context/Snippet
2026-09-27 01:00:00 UTC,C:\\Users\\CEO\\Desktop\\secret_passwords.txt,password,CONTENT_TEXT,1024,2026-09-26 12:00:00,admin password was updated
2026-09-27 01:01:00 UTC,C:\\Users\\CEO\\Documents\\vendor_kickback.docx,kickback,CONTENT_DOCX,45000,2026-09-25 10:00:00,kickback payout approved
"""
        device = ingest_scan_csv_file(
            csv_file_obj_or_path=csv_data,
            hostname="WS-FINANCE-01",
            scan_title="Q3 Internal Audit",
            custodian_name="Finance Director",
            drive_letter="C:\\",
        )

        self.assertEqual(device.hostname, "WS-FINANCE-01")
        self.assertEqual(device.total_matches_found, 2)
        self.assertEqual(FileEvidenceHit.objects.filter(device=device).count(), 2)

        metrics = get_scan_dashboard_metrics()
        self.assertEqual(metrics["total_devices"], 1)
        self.assertEqual(metrics["total_hits"], 2)

    def test_dashboard_and_export_views(self):
        # Create test device and hit
        device = ScannedDevice.objects.create(
            hostname="WS-EXEC-09",
            scan_title="Executive Audit",
            total_matches_found=1,
        )
        FileEvidenceHit.objects.create(
            device=device,
            file_path="C:\\pass.txt",
            filename="pass.txt",
            matched_keyword="password",
            match_type=FileEvidenceHit.MatchType.FILENAME,
            risk_score=90,
        )

        # Dashboard View
        resp = self.client.get(reverse("q_scan:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "WS-EXEC-09")

        # Detail View
        detail_resp = self.client.get(reverse("q_scan:device_detail", args=[device.id]))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Executive Audit")

        # Export CSV View
        export_resp = self.client.get(reverse("q_scan:export_csv"))
        self.assertEqual(export_resp.status_code, 200)
        self.assertIn(b"WS-EXEC-09", export_resp.content)

        # Delete Device
        delete_scanned_device(device.id)
        self.assertEqual(ScannedDevice.objects.count(), 0)
        self.assertEqual(FileEvidenceHit.objects.count(), 0)
