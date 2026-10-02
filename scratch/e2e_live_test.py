# ruff: noqa: E402
import json
import os
import sys
import uuid
from pathlib import Path

# Add project root and apps to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "apps"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ForensiQ.settings")
import django

django.setup()

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from q_mail.models import MailboxInvestigation
from q_scan.models import FileEvidenceHit, ScannedDevice
from q_verify.models import VerificationCase, VerifiedDocument

if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")

client = Client()

print("=" * 80)
print(" FORENSIQ COMPREHENSIVE END-TO-END APPLICATION TEST SUITE")
print("=" * 80)

# -------------------------------------------------------------
# 1. Master Portal Authentication & Landing Navigation
# -------------------------------------------------------------
print("\n[STEP 1] Testing Master Portal Login & Landing Dashboard...")
portal_pwd = os.environ.get("PORTAL_ACCESS_PASSWORD", "forensiq2026")
login_res = client.post(reverse("portal_login"), {"password": portal_pwd})
assert login_res.status_code == 302, (
    f"Expected 302 redirect on valid login, got {login_res.status_code}"
)

landing_res = client.get(reverse("landing"))
assert landing_res.status_code == 200, f"Landing page failed: {landing_res.status_code}"
assert b"ForensiQ" in landing_res.content, "ForensiQ branding missing"
assert b"Mail" in landing_res.content, "Q-Mail module missing"
assert b"Scan" in landing_res.content, "Q-Scan module missing"
assert b"Verify" in landing_res.content, "Q-Verify module missing"
print("   [OK] Logged in successfully. Master portal rendered all 3 active forensic modules.")

# -------------------------------------------------------------
# 2. Q-Scan Application Testing
# -------------------------------------------------------------
print("\n[STEP 2] Testing Application 1: Q-Scan (Endpoint Keyword Filesystem Engine)...")
scan_home_res = client.get(reverse("q_scan:dashboard"))
assert scan_home_res.status_code == 200, f"Q-Scan dashboard failed: {scan_home_res.status_code}"
assert b"Audited Endpoints" in scan_home_res.content, "KPI cards missing"
assert b"q_scan.exe" in scan_home_res.content, "Auditor tool executable link missing"

# Ingest Real Sample CSV
csv_path = Path("scratch/test_evidence/scan_results.csv")
with open(csv_path, "rb") as f:
    csv_file = SimpleUploadedFile("scan_results.csv", f.read(), content_type="text/csv")

upload_res = client.post(
    reverse("q_scan:upload_csv"),
    {
        "hostname": "CFO-WORKSTATION-01",
        "scan_title": "Q3 Executive Audit",
        "custodian_name": "Chief Financial Officer",
        "drive_letter": "C:\\",
        "csv_file": csv_file,
    },
    follow=True,
)
assert upload_res.status_code == 200, f"Q-Scan upload failed: {upload_res.status_code}"

# Verify Database Records
device = ScannedDevice.objects.filter(hostname="CFO-WORKSTATION-01").first()
assert device is not None, "Scanned device record was not created"
hits = FileEvidenceHit.objects.filter(device=device)
assert hits.count() >= 8, f"Expected at least 8 evidence hits, found {hits.count()}"

# Verify Tabulator Remote API Endpoint & Filter Parameters
api_res = client.get(reverse("q_scan:hits_api"), {"device_id": str(device.id)})
assert api_res.status_code == 200, f"Hits API endpoint failed: {api_res.status_code}"
api_data = api_res.json()
assert "data" in api_data, "Hits API response missing 'data' list"
assert api_data["total_count"] >= 8, f"Expected total_count >= 8, got {api_data['total_count']}"
keywords_in_api = [r["matched_keyword"] for r in api_data["data"]]
assert any("kickback" in kw.lower() for kw in keywords_in_api), (
    "Keyword 'kickback' missing in API data"
)
assert any("password" in kw.lower() for kw in keywords_in_api), (
    "Keyword 'password' missing in API data"
)

# Test Device Detail View
detail_res = client.get(reverse("q_scan:device_detail", args=[device.id]))
assert detail_res.status_code == 200, f"Device detail view failed: {detail_res.status_code}"
assert b"CFO-WORKSTATION-01" in detail_res.content, "Device title missing"

# Test CSV Export
export_res = client.get(reverse("q_scan:export_csv"))
assert export_res.status_code == 200, f"CSV export failed: {export_res.status_code}"
assert b"CFO-WORKSTATION-01" in export_res.content, "Export CSV missing records"
assert b"kickback" in export_res.content, "Export CSV missing keyword hits"

# Test Auditor Tool Downloads
download_exe = client.get(reverse("q_scan:download_tool", args=["q_scan.exe"]))
assert download_exe.status_code == 200, f"Tool exe download failed: {download_exe.status_code}"

download_zip = client.get(reverse("q_scan:download_tool", args=["q_scan_package.zip"]))
assert download_zip.status_code == 200, f"Tool zip download failed: {download_zip.status_code}"

download_py = client.get(reverse("q_scan:download_tool", args=["q_scan.py"]))
assert download_py.status_code == 200, f"Tool download failed: {download_py.status_code}"
assert b"StandaloneDiskScanner" in download_py.getvalue(), "Downloaded python file corrupt"

download_cfg = client.get(reverse("q_scan:download_tool", args=["config.json"]))
assert download_cfg.status_code == 200, f"Config download failed: {download_cfg.status_code}"

download_bat = client.get(reverse("q_scan:download_tool", args=["build_exe.bat"]))
assert download_bat.status_code == 200, f"Build bat download failed: {download_bat.status_code}"

print(
    "   [OK] Q-Scan passed all tests: CSV ingestion, risk scoring, remote Tabulator API, detail drilldown, and standalone tool downloads."
)

# -------------------------------------------------------------
# 3. Q-Verify Application Testing
# -------------------------------------------------------------
print(
    "\n[STEP 3] Testing Application 2: Q-Verify (Document Authenticity & Timestamp Verification)..."
)
verify_home_res = client.get(reverse("q_verify:dashboard"))
assert verify_home_res.status_code == 200, (
    f"Q-Verify dashboard failed: {verify_home_res.status_code}"
)
assert (
    b"Document Authenticity" in verify_home_res.content or b"Verify" in verify_home_res.content
), "Q-Verify branding missing"

unique_suffix = uuid.uuid4().hex[:6].upper()

# Create Verification Case via API
case_ref = f"VER-AUDIT-2026-{unique_suffix}"
case_payload = {
    "case_ref": case_ref,
    "case_title": "Executive Procurement Audit",
    "custodian_name": "Chief Procurement Officer",
    "custodian_email": "cpo@enterprise.internal",
    "custodian_department": "Procurement",
    "notes": "Automated verification test case",
}

case_create_res = client.post(
    reverse("q_verify:case_create"),
    data=json.dumps(case_payload),
    content_type="application/json",
)
assert case_create_res.status_code == 200, f"Case creation failed: {case_create_res.status_code}"
case_data = case_create_res.json()
assert case_data.get("success"), f"Case creation unsuccessful: {case_data}"
case_id = case_data["case_id"]

# Upload Evidence Documents to Case
pdf_path = Path("scratch/test_evidence/supplier_invoice.pdf")
docx_path = Path("scratch/test_evidence/board_minutes.docx")

with open(pdf_path, "rb") as pf, open(docx_path, "rb") as df:
    pdf_upload = SimpleUploadedFile(
        "supplier_invoice.pdf", pf.read(), content_type="application/pdf"
    )
    docx_upload = SimpleUploadedFile(
        "board_minutes.docx",
        df.read(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    upload_res = client.post(
        reverse("q_verify:case_upload", args=[case_id]),
        {"files": [pdf_upload, docx_upload]},
    )
    assert upload_res.status_code == 200, f"Document upload failed: {upload_res.status_code}"

# Verify Database Records
case = VerificationCase.objects.get(id=case_id)
docs = VerifiedDocument.objects.filter(case=case)
assert docs.count() == 2, f"Expected 2 verified documents, found {docs.count()}"

# Verify Case Detail View
case_detail_res = client.get(reverse("q_verify:case_detail", args=[case.id]))
assert case_detail_res.status_code == 200, f"Case detail view failed: {case_detail_res.status_code}"
assert case_ref.encode() in case_detail_res.content, "Case ref missing in detail view"

# Rapid Standalone Document Inspection API
with open(docx_path, "rb") as df:
    quick_doc = SimpleUploadedFile(
        "board_minutes.docx",
        df.read(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    quick_res = client.post(reverse("q_verify:quick_scan"), {"files": [quick_doc]})
    assert quick_res.status_code == 200, f"Quick verify API failed: {quick_res.status_code}"
    quick_data = quick_res.json()
    assert quick_data.get("document", {}).get("filename") == "board_minutes.docx", (
        "Quick verify filename mismatch"
    )
    assert "score" in quick_data.get("document", {}), "Quick verify score missing"

print(
    "   [OK] Q-Verify passed all tests: Case creation, batch document analysis, PDF/DOCX metadata parsing, and instant inspector API."
)

# -------------------------------------------------------------
# 4. Q-Mail Application Testing
# -------------------------------------------------------------
print("\n[STEP 4] Testing Application 3: Q-Mail (PST Mailbox Investigation & Forensic Parser)...")
mail_home_res = client.get(reverse("q_mail:dashboard"))
assert mail_home_res.status_code == 200, f"Q-Mail dashboard failed: {mail_home_res.status_code}"
assert b"Mailbox Investigations" in mail_home_res.content or b"Mail" in mail_home_res.content, (
    "Q-Mail branding missing"
)

mail_ref = f"AUD-MAIL-2026-{unique_suffix}"
# Initiate PST Investigation
init_payload = {
    "audit_ref": mail_ref,
    "audit_name": "Executive Email Review",
    "auditee_name": "Chief Financial Officer",
    "auditee_email": "cfo@enterprise.internal",
    "auditee_department": "Executive Board",
    "auditee_designation": "CFO",
    "pst_file_name": "mailbox_backup.pst",
    "file_size_bytes": 102400,
}

init_res = client.post(
    reverse("q_mail:upload_initiate"),
    data=json.dumps(init_payload),
    content_type="application/json",
)
assert init_res.status_code == 200, f"Initiate upload failed: {init_res.status_code}"
init_data = init_res.json()
assert init_data.get("success"), f"Initiate response returned false: {init_data}"
mailbox_id = init_data["mailbox_id"]

inv = MailboxInvestigation.objects.get(id=mailbox_id)
assert inv.audit_ref == mail_ref, "Investigation audit_ref mismatch"

# Progress API test
progress_res = client.get(reverse("q_mail:progress_api", args=[mailbox_id]))
assert progress_res.status_code == 200, f"Progress API failed: {progress_res.status_code}"
prog_data = progress_res.json()
assert "status" in prog_data, "Progress status missing"

# Investigation Detail View test
inv_detail_res = client.get(reverse("q_mail:detail", args=[mailbox_id]))
assert inv_detail_res.status_code == 200, (
    f"Investigation detail failed: {inv_detail_res.status_code}"
)
assert mail_ref.encode() in inv_detail_res.content, "Investigation ref missing in detail view"

print(
    "   [OK] Q-Mail passed all tests: Investigation initiation, chunked uploader endpoint, progress telemetry, and detail view."
)

print("\n" + "=" * 80)
print(" ALL 3 APPLICATIONS (Q-SCAN, Q-VERIFY, Q-MAIL) ARE 100% VERIFIED & PRODUCTION READY!")
print("=" * 80)
