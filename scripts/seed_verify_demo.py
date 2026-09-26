import os
import sys
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "apps"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ForensiQ.settings")
django.setup()

from datetime import UTC, datetime, timedelta  # noqa: E402

from q_verify.models import VerificationCase, VerifiedDocument  # noqa: E402
from q_verify.services import recompute_case_metrics  # noqa: E402


def seed_verify():
    print("Seeding Q-Verify demo data...")
    now = datetime.now(UTC)

    # 1. High-Value Vendor Contract Case
    case1, _ = VerificationCase.objects.get_or_create(
        case_ref="VER-PROC-2026-001",
        defaults={
            "case_title": "FY26 Strategic Sourcing & Vendor Agreement Audit",
            "custodian_name": "Rajesh Sharma",
            "custodian_email": "rajesh.sharma@hyundai-corp.internal",
            "custodian_department": "Global Procurement",
            "notes": "Comprehensive metadata audit of submitted vendor contracts, price adjustment letters, and quotation schedules.",
        },
    )

    docs_data = [
        {
            "filename": "Apex_Logistics_Master_Agreement_2026.pdf",
            "size": 2450000,
            "mime": "application/pdf",
            "ext": ".pdf",
            "meta_created": now - timedelta(days=60),
            "meta_modified": now - timedelta(days=2),  # Tampered: modified 58 days later
            "author": "Marcus Vance",
            "software": "Canva Online Editor / iLovePDF",
            "incremental": 3,
            "score": 35,
            "risk": VerifiedDocument.RiskLevel.HIGH_RISK_TAMPERED,
            "anomalies": [
                {
                    "code": "SUSPECT_SOFTWARE_CANVA",
                    "title": "Suspect Generator: Canva Online Editor",
                    "severity": "HIGH",
                    "description": "Document was assembled using Canva design software instead of native financial billing or legal systems.",
                    "penalty": 30,
                },
                {
                    "code": "PDF_INCREMENTAL_UPDATES",
                    "title": "PDF Multi-Revision Updates (3 Appended Trailers)",
                    "severity": "HIGH",
                    "description": "Document contains 3 incremental update revisions indicating post-signing overlays or altered text blocks.",
                    "penalty": 30,
                },
            ],
            "summary": "High probability of post-facto modification, backdating, or non-authentic software generation (2 critical flags).",
        },
        {
            "filename": "Hyundai_Standard_Procurement_Terms_v4.docx",
            "size": 890000,
            "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "ext": ".docx",
            "meta_created": now - timedelta(days=120),
            "meta_modified": now - timedelta(days=118),
            "author": "Legal Compliance Dept",
            "software": "Microsoft Office Word 16.0",
            "incremental": 0,
            "score": 95,
            "risk": VerifiedDocument.RiskLevel.AUTHENTIC,
            "anomalies": [],
            "summary": "No critical tampering indicators detected. Document metadata aligns with normal creation patterns.",
        },
        {
            "filename": "Valens_Trust_Escrow_Wire_Instruction.pdf",
            "size": 1200000,
            "mime": "application/pdf",
            "ext": ".pdf",
            "meta_created": now - timedelta(days=15),
            "meta_modified": now - timedelta(days=45),  # Inverted! Mod before Create
            "author": "Unknown / Stripped",
            "software": "Adobe Photoshop 2024",
            "incremental": 1,
            "score": 20,
            "risk": VerifiedDocument.RiskLevel.HIGH_RISK_TAMPERED,
            "anomalies": [
                {
                    "code": "MODIFIED_BEFORE_CREATED",
                    "title": "Timestamp Inversion (Mod < Create)",
                    "severity": "CRITICAL",
                    "description": "Embedded modification date is earlier than creation date. Indicates manual timestamp alteration or backdated metadata injection.",
                    "penalty": 35,
                },
                {
                    "code": "SUSPECT_SOFTWARE_PHOTOSHOP",
                    "title": "Suspect Generator: Adobe Photoshop",
                    "severity": "CRITICAL",
                    "description": "Document was edited or created using photo editing software (Adobe Photoshop).",
                    "penalty": 35,
                },
            ],
            "summary": "Critical forensic tampering detected: Inverted timestamps and Adobe Photoshop raster editing on official banking document.",
        },
        {
            "filename": "Q2_Logistics_Tender_Scoring_Matrix.xlsx",
            "size": 1450000,
            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "ext": ".xlsx",
            "meta_created": now - timedelta(days=30),
            "meta_modified": now - timedelta(days=30),
            "author": "Arun Verma",
            "software": "Microsoft Excel 16.0",
            "incremental": 0,
            "score": 100,
            "risk": VerifiedDocument.RiskLevel.AUTHENTIC,
            "anomalies": [],
            "summary": "Authentic spreadsheet workbook with consistent authorship and timestamps.",
        },
        {
            "filename": "Titan_Consulting_Fee_Addendum_Scanned.png",
            "size": 3100000,
            "mime": "image/png",
            "ext": ".png",
            "meta_created": now - timedelta(days=10),
            "meta_modified": now - timedelta(days=10),
            "author": "Sarah Jenkins",
            "software": "GIMP 2.10.34",
            "incremental": 0,
            "score": 65,
            "risk": VerifiedDocument.RiskLevel.SUSPICIOUS,
            "anomalies": [
                {
                    "code": "SUSPECT_SOFTWARE_GIMP",
                    "title": "Suspect Generator: GIMP Image Editor",
                    "severity": "HIGH",
                    "description": "Image document was edited using open-source raster graphics editor GIMP.",
                    "penalty": 35,
                }
            ],
            "summary": "Detected image manipulation software in scanned contract header.",
        },
    ]

    for d in docs_data:
        VerifiedDocument.objects.update_or_create(
            case=case1,
            filename=d["filename"],
            defaults={
                "file_size_bytes": d["size"],
                "mime_type": d["mime"],
                "file_extension": d["ext"],
                "sha256_hash": f"e3b0c442{d['filename'][:8].encode().hex()}991b7852b855",
                "file_created_at": d["meta_created"],
                "file_modified_at": d["meta_modified"],
                "meta_created_at": d["meta_created"],
                "meta_modified_at": d["meta_modified"],
                "meta_author": d["author"],
                "meta_software": d["software"],
                "incremental_updates_count": d["incremental"],
                "authenticity_score": d["score"],
                "risk_level": d["risk"],
                "has_timestamp_anomaly": any(
                    "TIMESTAMP" in a["code"] or "MODIFIED" in a["code"] for a in d["anomalies"]
                ),
                "has_software_anomaly": any("SOFTWARE" in a["code"] for a in d["anomalies"]),
                "has_structural_anomaly": d["incremental"] > 0,
                "anomalies": d["anomalies"],
                "summary": d["summary"],
                "raw_metadata": {
                    "software": d["software"],
                    "author": d["author"],
                    "created": str(d["meta_created"]),
                    "modified": str(d["meta_modified"]),
                },
            },
        )

    recompute_case_metrics(case1)
    print(
        f"Seeded case {case1.case_ref} with {case1.total_documents} documents (Avg Score: {case1.average_authenticity_score})."
    )


if __name__ == "__main__":
    seed_verify()
