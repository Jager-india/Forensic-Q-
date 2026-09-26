"""
Q-Verify Office Forensic Inspector
Extracts Dublin Core and Extended Application properties from DOCX, XLSX, and PPTX packages.
"""

import hashlib
import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET
from loguru import logger

from .models_data import ParsedMetadata


class OfficeInspector:
    """
    Forensic metadata parser for Microsoft Office OpenXML documents (DOCX, XLSX, PPTX).
    Extracts author chains, revision iterations, total editing minutes, and software versions.
    """

    MIME_MAP = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }

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
        ext = Path(filename).suffix.lower()
        mime_type = cls.MIME_MAP.get(ext, "application/vnd.openxmlformats-officedocument")

        raw_dict: dict[str, Any] = {
            "format": f"Office OpenXML ({ext.upper()})",
            "filesize_bytes": file_size,
        }

        meta_created_at: datetime | None = None
        meta_modified_at: datetime | None = None
        author = ""
        last_modified_by = ""
        title = ""
        subject = ""
        company = ""
        application = ""
        app_version = ""
        revision = ""
        total_time_mins = 0

        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
                # 1. Parse docProps/core.xml (Dublin Core metadata)
                if "docProps/core.xml" in zf.namelist():
                    core_xml = zf.read("docProps/core.xml")
                    core_root = ET.fromstring(core_xml)
                    raw_dict["core_properties"] = {}

                    for elem in core_root:
                        tag_name = elem.tag.split("}")[-1]
                        text_val = (elem.text or "").strip()
                        raw_dict["core_properties"][tag_name] = text_val

                        if tag_name == "creator":
                            author = text_val
                        elif tag_name == "lastModifiedBy":
                            last_modified_by = text_val
                        elif tag_name == "title":
                            title = text_val
                        elif tag_name == "subject":
                            subject = text_val
                        elif tag_name == "revision":
                            revision = text_val
                        elif tag_name == "created":
                            meta_created_at = cls._parse_iso_date(text_val)
                        elif tag_name == "modified":
                            meta_modified_at = cls._parse_iso_date(text_val)

                # 2. Parse docProps/app.xml (Extended properties: Application, Company, TotalTime)
                if "docProps/app.xml" in zf.namelist():
                    app_xml = zf.read("docProps/app.xml")
                    app_root = ET.fromstring(app_xml)
                    raw_dict["app_properties"] = {}

                    for elem in app_root:
                        tag_name = elem.tag.split("}")[-1]
                        text_val = (elem.text or "").strip()
                        raw_dict["app_properties"][tag_name] = text_val

                        if tag_name == "Application":
                            application = text_val
                        elif tag_name == "AppVersion":
                            app_version = text_val
                        elif tag_name == "Company":
                            company = text_val
                        elif tag_name == "TotalTime":
                            try:
                                total_time_mins = int(text_val)
                            except ValueError:
                                total_time_mins = 0

                # 3. Parse docProps/custom.xml if present
                if "docProps/custom.xml" in zf.namelist():
                    try:
                        custom_xml = zf.read("docProps/custom.xml")
                        custom_root = ET.fromstring(custom_xml)
                        custom_dict = {}
                        for prop in custom_root:
                            p_name = prop.attrib.get("name", "")
                            p_val = "".join(prop.itertext()).strip()
                            if p_name:
                                custom_dict[p_name] = p_val
                        raw_dict["custom_properties"] = custom_dict
                    except Exception as e:
                        logger.debug("Failed parsing custom.xml: {}", e)

        except Exception as e:
            logger.warning("Error inspecting Office document {}: {}", filename, e)
            raw_dict["parser_error"] = str(e)

        software_str = f"{application} {app_version}".strip() or "Microsoft Office"

        return ParsedMetadata(
            filename=filename,
            file_size_bytes=file_size,
            mime_type=mime_type,
            file_extension=ext,
            sha256_hash=sha256,
            file_created_at=file_created_at,
            file_modified_at=file_modified_at,
            meta_created_at=meta_created_at,
            meta_modified_at=meta_modified_at,
            meta_author=author,
            meta_creator=author,
            meta_last_modified_by=last_modified_by,
            meta_company=company,
            meta_software=software_str,
            meta_title=title,
            meta_subject=subject,
            revision_number=revision,
            editing_time_minutes=total_time_mins,
            raw_dict=raw_dict,
        )

    @staticmethod
    def _parse_iso_date(date_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            # Handle standard ISO: 2026-03-15T14:30:22Z
            clean_str = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except Exception as e:
            logger.debug("Failed parsing ISO date {}: {}", date_str, e)
            return None
