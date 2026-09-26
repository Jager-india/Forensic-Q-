"""
Q-Verify Business Logic & Forensic Ingestion Services
Follows agentic-django principles: pure domain workflows, atomic transactions, and automated metric aggregation.
"""

from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Count, Q
from loguru import logger

from .backend import inspect_document
from .models import VerificationCase, VerifiedDocument


@transaction.atomic
def create_verification_case(
    *,
    case_ref: str,
    case_title: str,
    custodian_name: str,
    custodian_email: str = "",
    custodian_department: str = "",
    notes: str = "",
) -> VerificationCase:
    """
    Initializes a new document verification audit case.
    """
    case = VerificationCase.objects.create(
        case_ref=case_ref.strip(),
        case_title=case_title.strip(),
        custodian_name=custodian_name.strip(),
        custodian_email=custodian_email.strip().lower(),
        custodian_department=custodian_department.strip(),
        notes=notes.strip(),
        status=VerificationCase.CaseStatus.PENDING,
    )
    logger.info("Created Verification Case: {} ({})", case.case_ref, case.case_title)
    return case


@transaction.atomic
def ingest_and_verify_document(
    *,
    file_bytes: bytes,
    filename: str,
    case: VerificationCase | None = None,
    save_disk: bool = True,
    file_created_at: datetime | None = None,
    file_modified_at: datetime | None = None,
) -> VerifiedDocument:
    """
    Executes forensic metadata inspection, anomaly detection, and persistence.
    """
    # 1. Inspect file and compute authenticity score
    result = inspect_document(
        file_bytes=file_bytes,
        filename=filename,
        file_created_at=file_created_at,
        file_modified_at=file_modified_at,
    )
    meta = result.metadata

    # 2. Persist physical file if configured
    storage_path = ""
    if save_disk:
        folder_key = str(case.id) if case else "quick_scans"
        dest_dir = Path(settings.MEDIA_ROOT) / "verify" / folder_key
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / f"{meta.sha256_hash[:16]}_{filename}"
        with open(dest_file, "wb") as f:
            f.write(file_bytes)
        storage_path = str(dest_file)

    # 3. Serialize anomalies
    anomalies_data = [
        {
            "code": a.code,
            "title": a.title,
            "severity": a.severity,
            "description": a.description,
            "penalty": a.penalty,
        }
        for a in result.anomalies
    ]

    # 4. Save VerifiedDocument record
    doc = VerifiedDocument.objects.create(
        case=case,
        filename=filename,
        file_size_bytes=meta.file_size_bytes,
        mime_type=meta.mime_type,
        file_extension=meta.file_extension,
        sha256_hash=meta.sha256_hash,
        storage_path=storage_path,
        file_created_at=meta.file_created_at or datetime.now(UTC),
        file_modified_at=meta.file_modified_at or datetime.now(UTC),
        meta_created_at=meta.meta_created_at,
        meta_modified_at=meta.meta_modified_at,
        meta_author=meta.meta_author,
        meta_creator=meta.meta_creator,
        meta_producer=meta.meta_producer,
        meta_software=meta.meta_software,
        meta_company=meta.meta_company,
        meta_title=meta.meta_title,
        meta_subject=meta.meta_subject,
        incremental_updates_count=meta.incremental_updates_count,
        editing_time_minutes=meta.editing_time_minutes,
        revision_number=meta.revision_number,
        authenticity_score=result.authenticity_score,
        risk_level=result.risk_level,
        has_timestamp_anomaly=result.has_timestamp_anomaly,
        has_software_anomaly=result.has_software_anomaly,
        has_structural_anomaly=result.has_structural_anomaly,
        anomalies=anomalies_data,
        raw_metadata=meta.raw_dict,
        summary=result.summary,
    )

    # 5. Update case aggregate KPIs
    if case:
        recompute_case_metrics(case)

    logger.info(
        "Verified document {} [Score: {}/100, Risk: {}]",
        doc.filename,
        doc.authenticity_score,
        doc.risk_level,
    )
    return doc


def recompute_case_metrics(case: VerificationCase) -> None:
    """
    Updates total counts, risk breakdowns, and average authenticity score for a case.
    """
    stats = VerifiedDocument.objects.filter(case=case).aggregate(
        total=Count("id"),
        authentic=Count("id", filter=Q(risk_level=VerifiedDocument.RiskLevel.AUTHENTIC)),
        suspicious=Count("id", filter=Q(risk_level=VerifiedDocument.RiskLevel.SUSPICIOUS)),
        tampered=Count("id", filter=Q(risk_level=VerifiedDocument.RiskLevel.HIGH_RISK_TAMPERED)),
        avg_score=Avg("authenticity_score"),
    )

    case.total_documents = stats["total"] or 0
    case.authentic_count = stats["authentic"] or 0
    case.suspicious_count = stats["suspicious"] or 0
    case.tampered_count = stats["tampered"] or 0
    case.average_authenticity_score = round(stats["avg_score"] or 100.0, 1)
    case.status = VerificationCase.CaseStatus.COMPLETED
    case.save(
        update_fields=[
            "total_documents",
            "authentic_count",
            "suspicious_count",
            "tampered_count",
            "average_authenticity_score",
            "status",
            "updated_at",
        ]
    )
