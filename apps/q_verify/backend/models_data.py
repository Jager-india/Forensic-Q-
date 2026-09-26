"""
Q-Verify Backend Data Structures
Dataclasses for metadata extraction, anomaly detection, and authenticity scoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AnomalyFlag:
    code: str
    title: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    penalty: int


@dataclass
class ParsedMetadata:
    filename: str
    file_size_bytes: int
    mime_type: str
    file_extension: str
    sha256_hash: str

    # File System Dates
    file_created_at: datetime | None = None
    file_modified_at: datetime | None = None

    # Embedded Metadata Dates
    meta_created_at: datetime | None = None
    meta_modified_at: datetime | None = None

    # Author & Application Metadata
    meta_author: str = ""
    meta_creator: str = ""
    meta_producer: str = ""
    meta_software: str = ""
    meta_last_modified_by: str = ""
    meta_company: str = ""
    meta_title: str = ""
    meta_subject: str = ""

    # Structural & Forensic Indicators
    incremental_updates_count: int = 0
    editing_time_minutes: int = 0
    revision_number: str = ""
    is_encrypted: bool = False

    # Raw Metadata Dictionary
    raw_dict: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    metadata: ParsedMetadata
    authenticity_score: int  # 0 to 100
    risk_level: str  # AUTHENTIC, SUSPICIOUS, HIGH_RISK_TAMPERED
    anomalies: list[AnomalyFlag] = field(default_factory=list)
    has_timestamp_anomaly: bool = False
    has_software_anomaly: bool = False
    has_structural_anomaly: bool = False
    summary: str = ""
