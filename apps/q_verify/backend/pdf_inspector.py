"""
Q-Verify PDF Forensic Inspector
Extracts PDF Document Info, XMP metadata, trailer revisions, and incremental updates.
"""

import hashlib
import io
import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from pypdf import PdfReader

from .models_data import ParsedMetadata


class PDFInspector:
    """
    Forensic parser for PDF documents. Extracts metadata, detects incremental updates,
    and identifies PDF generator software signatures.
    """

    @classmethod
    def inspect(
        cls,
        file_bytes: bytes,
        filename: str,
        file_created_at: datetime | None = None,
        file_modified_at: datetime | None = None,
    ) -> ParsedMetadata:
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        file_size = len(file_bytes)
        ext = Path(filename).suffix.lower() or ".pdf"

        # Binary analysis for incremental updates (count %%EOF markers)
        eof_matches = list(re.finditer(rb"%%EOF", file_bytes))
        incremental_updates = max(0, len(eof_matches) - 1)

        raw_dict: dict[str, Any] = {
            "format": "PDF",
            "filesize_bytes": file_size,
            "eof_markers_count": len(eof_matches),
            "incremental_updates_count": incremental_updates,
        }

        meta_created_at: datetime | None = None
        meta_modified_at: datetime | None = None
        author = ""
        creator = ""
        producer = ""
        title = ""
        subject = ""
        is_encrypted = False

        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            is_encrypted = reader.is_encrypted

            if not is_encrypted:
                doc_info = reader.metadata
                if doc_info:
                    raw_dict["doc_info"] = {k: str(v) for k, v in doc_info.items()}

                    author = str(doc_info.get("/Author", "")).strip()
                    creator = str(doc_info.get("/Creator", "")).strip()
                    producer = str(doc_info.get("/Producer", "")).strip()
                    title = str(doc_info.get("/Title", "")).strip()
                    subject = str(doc_info.get("/Subject", "")).strip()

                    raw_cdate = doc_info.get("/CreationDate")
                    if raw_cdate:
                        meta_created_at = cls._parse_pdf_date(str(raw_cdate))

                    raw_mdate = doc_info.get("/ModDate")
                    if raw_mdate:
                        meta_modified_at = cls._parse_pdf_date(str(raw_mdate))

                # Extract XMP metadata if present
                try:
                    if hasattr(reader, "xmp_metadata") and reader.xmp_metadata:
                        xmp = reader.xmp_metadata
                        raw_dict["xmp_metadata"] = {
                            "dc_creator": getattr(xmp, "dc_creator", None),
                            "dc_title": getattr(xmp, "dc_title", None),
                            "xmp_create_date": str(getattr(xmp, "xmp_create_date", "")),
                            "xmp_modify_date": str(getattr(xmp, "xmp_modify_date", "")),
                            "pdf_producer": getattr(xmp, "pdf_producer", None),
                        }
                        if not author and getattr(xmp, "dc_creator", None):
                            author = ", ".join(xmp.dc_creator)
                        if not meta_created_at and getattr(xmp, "xmp_create_date", None):
                            meta_created_at = cls._normalize_dt(xmp.xmp_create_date)
                        if not meta_modified_at and getattr(xmp, "xmp_modify_date", None):
                            meta_modified_at = cls._normalize_dt(xmp.xmp_modify_date)
                except Exception as e:
                    logger.debug("Failed extracting XMP metadata: {}", e)

                raw_dict["page_count"] = len(reader.pages)
        except Exception as e:
            logger.warning("Error parsing PDF metadata for {}: {}", filename, e)
            raw_dict["parser_error"] = str(e)

        return ParsedMetadata(
            filename=filename,
            file_size_bytes=file_size,
            mime_type="application/pdf",
            file_extension=ext,
            sha256_hash=sha256,
            file_created_at=file_created_at,
            file_modified_at=file_modified_at,
            meta_created_at=meta_created_at,
            meta_modified_at=meta_modified_at,
            meta_author=author,
            meta_creator=creator,
            meta_producer=producer,
            meta_software=f"{creator} / {producer}".strip(" /"),
            meta_title=title,
            meta_subject=subject,
            incremental_updates_count=incremental_updates,
            is_encrypted=is_encrypted,
            raw_dict=raw_dict,
        )

    @classmethod
    def _parse_pdf_date(cls, date_str: str) -> datetime | None:
        """
        Parses standard PDF Date format: D:YYYYMMDDHHmmSSOHH'mm'
        e.g. D:20260315143022+05'30' or 2026-03-15T14:30:22
        """
        if not date_str:
            return None

        clean_str = date_str.strip().lstrip("D:").replace("'", "")
        # Try ISO format
        if "T" in clean_str or "-" in clean_str:
            try:
                dt = datetime.fromisoformat(clean_str)
                return cls._normalize_dt(dt)
            except Exception as e:
                logger.debug("ISO date parse fallback for {}: {}", clean_str, e)

        # Match standard PDF timestamp: YYYYMMDDHHmmss
        pattern = re.compile(
            r"^(?P<year>\d{4})"
            r"(?P<month>\d{2})?"
            r"(?P<day>\d{2})?"
            r"(?P<hour>\d{2})?"
            r"(?P<minute>\d{2})?"
            r"(?P<second>\d{2})?"
            r"(?P<tz_sign>[+\-Z])?"
            r"(?P<tz_hour>\d{2})?"
            r"(?P<tz_min>\d{2})?"
        )
        match = pattern.match(clean_str)
        if not match:
            return None

        gd = match.groupdict()
        try:
            year = int(gd["year"])
            month = int(gd["month"] or 1)
            day = int(gd["day"] or 1)
            hour = int(gd["hour"] or 0)
            minute = int(gd["minute"] or 0)
            second = int(gd["second"] or 0)

            tz = UTC
            if gd["tz_sign"] in ("+", "-") and gd["tz_hour"]:
                offset_hrs = int(gd["tz_hour"])
                offset_mins = int(gd["tz_min"] or 0)
                delta = timedelta(hours=offset_hrs, minutes=offset_mins)
                if gd["tz_sign"] == "-":
                    delta = -delta
                tz = timezone(delta)

            dt = datetime(year, month, day, hour, minute, second, tzinfo=tz)
            return dt.astimezone(UTC)
        except Exception as e:
            logger.debug("Failed parsing PDF date {}: {}", date_str, e)
            return None

    @staticmethod
    def _normalize_dt(val: Any) -> datetime | None:
        if not val:
            return None
        if isinstance(val, datetime):
            if val.tzinfo is None:
                return val.replace(tzinfo=UTC)
            return val.astimezone(UTC)
        return None
