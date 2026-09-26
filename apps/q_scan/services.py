"""
Q-Scan Business Logic & Mutation Services
Handles evidence CSV ingestion, atomic batch database writes, and scoring classification.
"""

import csv
import io
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from django.db import transaction
from django.utils.dateparse import parse_datetime
from loguru import logger

from .models import FileEvidenceHit, ScannedDevice

HIGH_RISK_KEYWORDS = {
    "password",
    "credentials",
    "secret",
    "private_key",
    "id_rsa",
    "kickback",
    "bribe",
    "shadow",
    "offshore",
    "unauthorized",
    "exploit",
    "backdoor",
}

MEDIUM_RISK_KEYWORDS = {
    "salary",
    "payroll",
    "invoice",
    "ledger",
    "confidential",
    "nda",
    "audit",
    "wire_transfer",
    "p&l",
}


def _calculate_risk_score(keyword: str, path: str, match_type: str) -> int:
    """
    Computes a forensic risk score between 10 and 95 based on keyword severity and location.
    """
    kw_lower = keyword.lower().strip()
    path_lower = path.lower()

    if any(k in kw_lower for k in HIGH_RISK_KEYWORDS):
        score = 85
    elif any(k in kw_lower for k in MEDIUM_RISK_KEYWORDS):
        score = 65
    else:
        score = 45

    # Elevation for system/security/hidden paths
    if (
        "appdata" in path_lower
        or "desktop" in path_lower
        or "temp" in path_lower
        or ".env" in path_lower
    ):
        score = min(98, score + 10)

    # Elevation for document/spreadsheet content hits vs filename
    if "CONTENT" in match_type:
        score = min(99, score + 5)

    return score


def _parse_timestamp(raw_val: str) -> datetime | None:
    """
    Parses timestamp string safely to UTC datetime object.
    """
    if not raw_val or not raw_val.strip():
        return None
    val = raw_val.strip()
    # Strip UTC suffix if present
    if val.endswith(" UTC"):
        val = val[:-4].strip()
    # Try ISO format
    dt = parse_datetime(val)
    if dt:
        return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt

    # Try standard forensic formats
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
        try:
            parsed = datetime.strptime(val, fmt)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


@transaction.atomic
def ingest_scan_csv_file(
    *,
    csv_file_obj_or_path: Any,
    hostname: str = "ENDPOINT-WORKSTATION",
    scan_title: str = "Endpoint Keyword Sweep",
    custodian_name: str = "",
    drive_letter: str = "C:\\",
) -> ScannedDevice:
    """
    Atomically ingests a scan_results.csv report and creates batch evidence records.
    """
    # Read raw content
    if hasattr(csv_file_obj_or_path, "read"):
        raw_data = csv_file_obj_or_path.read()
        if isinstance(raw_data, bytes):
            text_data = raw_data.decode("utf-8-sig", errors="replace")
        else:
            text_data = str(raw_data)
    elif isinstance(csv_file_obj_or_path, Path):
        text_data = csv_file_obj_or_path.read_text(encoding="utf-8-sig", errors="replace")
    elif isinstance(csv_file_obj_or_path, str):
        if "\n" in csv_file_obj_or_path or "," in csv_file_obj_or_path:
            text_data = csv_file_obj_or_path
        elif Path(csv_file_obj_or_path).exists():
            text_data = Path(csv_file_obj_or_path).read_text(encoding="utf-8-sig", errors="replace")
        else:
            text_data = csv_file_obj_or_path
    else:
        text_data = str(csv_file_obj_or_path)

    reader = csv.reader(io.StringIO(text_data))
    _header = next(reader, None)

    # Create ScannedDevice container
    device = ScannedDevice.objects.create(
        hostname=hostname.strip() or "ENDPOINT-PC",
        scan_title=scan_title.strip() or "Forensic Drive Scan",
        custodian_name=custodian_name.strip(),
        drive_letter=drive_letter.strip(),
        status=ScannedDevice.ScanStatus.IMPORTED,
        scan_completed_at=datetime.now(UTC),
    )

    batch: list[FileEvidenceHit] = []
    total_bytes = 0
    total_hits = 0

    for row in reader:
        if not row or len(row) < 3:
            continue

        # Flexible column mapping
        timestamp_str = row[0] if len(row) > 0 else ""
        file_path = row[1] if len(row) > 1 else ""
        keyword = row[2] if len(row) > 2 else ""
        match_type_raw = row[3] if len(row) > 3 else "CONTENT_TEXT"
        size_raw = row[4] if len(row) > 4 else "0"
        mod_time_str = row[5] if len(row) > 5 else ""
        snippet = row[6] if len(row) > 6 else ""

        # Parse numeric size
        size_bytes = 0
        try:
            # Handle plain digits or formatted string like '1.20 MB'
            size_clean = size_raw.split()[0].replace(",", "")
            size_bytes = int(float(size_clean))
        except (ValueError, IndexError):
            size_bytes = 0

        total_bytes += size_bytes

        # Parse Path & Filename
        clean_path = file_path.strip()
        # If it's a nested zip/office path like 'C:\foo.zip -> [bar.txt]'
        base_path = clean_path.split(" -> ")[0] if " -> " in clean_path else clean_path
        filename = Path(base_path).name or "unknown"
        ext = Path(filename).suffix.lower()

        # Normalize match type
        match_type_upper = match_type_raw.strip().upper()
        if "NAME" in match_type_upper:
            match_type = FileEvidenceHit.MatchType.FILENAME
        elif "DOCX" in match_type_upper:
            match_type = FileEvidenceHit.MatchType.CONTENT_DOCX
        elif "XLSX" in match_type_upper:
            match_type = FileEvidenceHit.MatchType.CONTENT_XLSX
        elif "PPTX" in match_type_upper:
            match_type = FileEvidenceHit.MatchType.CONTENT_PPTX
        elif "ZIP_OFFICE" in match_type_upper:
            match_type = FileEvidenceHit.MatchType.CONTENT_ZIP_OFFICE
        elif "ZIP" in match_type_upper:
            match_type = FileEvidenceHit.MatchType.CONTENT_ZIP_ENTRY
        else:
            match_type = FileEvidenceHit.MatchType.CONTENT_TEXT

        risk_score = _calculate_risk_score(keyword, clean_path, match_type)

        det_time = _parse_timestamp(timestamp_str)
        mod_time = _parse_timestamp(mod_time_str)

        hit = FileEvidenceHit(
            device=device,
            file_path=clean_path[:1024],
            filename=filename[:255],
            extension=ext[:32],
            file_size_bytes=size_bytes,
            matched_keyword=keyword[:128],
            match_type=match_type,
            snippet=snippet,
            file_modified_at=mod_time,
            detection_timestamp=det_time or datetime.now(UTC),
            risk_score=risk_score,
        )
        batch.append(hit)
        total_hits += 1

        # Bulk insert in batches of 250
        if len(batch) >= 250:
            FileEvidenceHit.objects.bulk_create(batch)
            batch = []

    if batch:
        FileEvidenceHit.objects.bulk_create(batch)

    # Update summary totals on ScannedDevice
    device.total_matches_found = total_hits
    device.total_bytes_scanned = total_bytes
    device.save(update_fields=["total_matches_found", "total_bytes_scanned", "updated_at"])

    logger.info(
        "Successfully imported Q-Scan report for device '{}' ({} hits, {} bytes)",
        device.hostname,
        total_hits,
        total_bytes,
    )
    return device


@transaction.atomic
def delete_scanned_device(device_id: str | uuid.UUID) -> bool:
    """
    Atomically deletes a scanned device and all its associated evidence hits.
    """
    try:
        device = ScannedDevice.objects.get(id=device_id)
        device.delete()
        logger.info("Deleted scanned device case ID {}", device_id)
        return True
    except ScannedDevice.DoesNotExist:
        return False


@transaction.atomic
def update_evidence_hit_review(
    hit_id: str | uuid.UUID, *, is_reviewed: bool, reviewer_notes: str = ""
) -> FileEvidenceHit | None:
    """
    Updates the analyst review status on an individual evidence hit.
    """
    try:
        hit = FileEvidenceHit.objects.get(id=hit_id)
        hit.is_reviewed = is_reviewed
        hit.reviewer_notes = reviewer_notes
        hit.save(update_fields=["is_reviewed", "reviewer_notes", "updated_at"])
        return hit
    except FileEvidenceHit.DoesNotExist:
        return None
