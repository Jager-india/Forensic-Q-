"""
Q-Verify Automated Test Suite
Unit tests for PDF inspector, Office inspector, Discrepancy analyzer, and API endpoints.
"""

import io
import zipfile
from datetime import UTC, datetime, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .backend import DiscrepancyAnalyzer, OfficeInspector, ParsedMetadata
from .models import VerificationCase, VerifiedDocument
from .services import create_verification_case, ingest_and_verify_document


class QVerifyUnitTests(TestCase):
    def setUp(self):
        self.client = Client()
        session = self.client.session
        session["portal_authenticated"] = True
        session.save()

    def test_discrepancy_analyzer_tampered_timestamp(self):
        now = datetime.now(UTC)
        meta = ParsedMetadata(
            filename="tampered_contract.pdf",
            file_size_bytes=1024,
            mime_type="application/pdf",
            file_extension=".pdf",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            meta_created_at=now,
            meta_modified_at=now - timedelta(days=30),  # Modified before Created!
            meta_software="Canva Online Editor",
            incremental_updates_count=2,
        )

        result = DiscrepancyAnalyzer.analyze(meta)
        self.assertLess(result.authenticity_score, 50)
        self.assertEqual(result.risk_level, "HIGH_RISK_TAMPERED")
        self.assertTrue(result.has_timestamp_anomaly)
        self.assertTrue(result.has_software_anomaly)
        self.assertTrue(result.has_structural_anomaly)

    def test_office_inspector(self):
        # Create synthetic docProps/core.xml and app.xml in zip stream
        core_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                           xmlns:dc="http://purl.org/dc/elements/1.1/"
                           xmlns:dcterms="http://purl.org/dc/terms/">
            <dc:creator>John Auditor</dc:creator>
            <cp:lastModifiedBy>Jane Reviewer</cp:lastModifiedBy>
            <cp:revision>5</cp:revision>
            <dcterms:created>2026-03-01T10:00:00Z</dcterms:created>
            <dcterms:modified>2026-03-05T14:30:00Z</dcterms:modified>
        </cp:coreProperties>"""

        app_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
            <Application>Microsoft Office Word</Application>
            <AppVersion>16.0000</AppVersion>
            <Company>Hyundai Corp</Company>
            <TotalTime>120</TotalTime>
        </Properties>"""

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("docProps/core.xml", core_xml)
            zf.writestr("docProps/app.xml", app_xml)

        zip_bytes = buf.getvalue()
        meta = OfficeInspector.inspect(zip_bytes, "audit_memo.docx")

        self.assertEqual(meta.meta_author, "John Auditor")
        self.assertEqual(meta.meta_last_modified_by, "Jane Reviewer")
        self.assertEqual(meta.meta_company, "Hyundai Corp")
        self.assertEqual(meta.editing_time_minutes, 120)
        self.assertEqual(meta.revision_number, "5")

    def test_create_case_and_ingest_document_service(self):
        case = create_verification_case(
            case_ref="VER-TEST-2026-001",
            case_title="Supplier Invoice Authenticity Review",
            custodian_name="Amitabh Sen",
            custodian_department="Procurement",
        )
        self.assertEqual(case.status, VerificationCase.CaseStatus.PENDING)

        dummy_pdf = b"%PDF-1.4\n1 0 obj\n<< /Title (Invoice #9901) >>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF"

        doc = ingest_and_verify_document(
            file_bytes=dummy_pdf,
            filename="Invoice_9901.pdf",
            case=case,
            save_disk=False,
        )

        self.assertEqual(doc.case, case)
        self.assertEqual(doc.filename, "Invoice_9901.pdf")

        case.refresh_from_db()
        self.assertEqual(case.total_documents, 1)
        self.assertEqual(case.status, VerificationCase.CaseStatus.COMPLETED)

    def test_quick_scan_api(self):
        dummy_docx = b"PK\x03\x04" + b"\x00" * 30
        file = SimpleUploadedFile(
            "quick_contract.docx", dummy_docx, content_type="application/octet-stream"
        )

        url = reverse("q_verify:quick_scan")
        res = self.client.post(url, data={"files": file})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["document"]["filename"], "quick_contract.docx")

    def test_case_detail_and_tabulator_grid_api(self):
        case = VerificationCase.objects.create(
            case_ref="VER-GRID-001",
            case_title="Grid Test Case",
            custodian_name="Test Custodian",
        )
        VerifiedDocument.objects.create(
            case=case,
            filename="Doc_Alpha.pdf",
            authenticity_score=95,
            risk_level=VerifiedDocument.RiskLevel.AUTHENTIC,
        )
        VerifiedDocument.objects.create(
            case=case,
            filename="Doc_Beta.pdf",
            authenticity_score=35,
            risk_level=VerifiedDocument.RiskLevel.HIGH_RISK_TAMPERED,
        )

        # 1. Test case detail view
        detail_url = reverse("q_verify:case_detail", kwargs={"case_id": case.id})
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, 200)

        # 2. Test Tabulator Grid API
        grid_url = reverse("q_verify:documents_grid_api", kwargs={"case_id": case.id})
        grid_res = self.client.get(grid_url)
        self.assertEqual(grid_res.status_code, 200)
        grid_data = grid_res.json()
        self.assertEqual(grid_data["total_count"], 2)
        self.assertEqual(len(grid_data["data"]), 2)

        # 3. Test filter by search
        search_res = self.client.get(f"{grid_url}?search=Alpha")
        self.assertEqual(search_res.status_code, 200)
        self.assertEqual(search_res.json()["total_count"], 1)
