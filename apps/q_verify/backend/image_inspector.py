"""
Q-Verify Image Forensic Inspector
Extracts EXIF and XMP metadata from JPEG, PNG, and TIFF images to detect photo editing and timestamps.
"""

import hashlib
import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger
from PIL import ExifTags, Image

from .models_data import ParsedMetadata


class ImageInspector:
    """
    Forensic image metadata inspector. Extracts EXIF camera parameters, software generator tags,
    and original vs digitized timestamps.
    """

    MIME_MAP = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".webp": "image/webp",
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
        mime_type = cls.MIME_MAP.get(ext, "image/jpeg")

        raw_dict: dict[str, Any] = {
            "format": f"Image ({ext.upper().lstrip('.')})",
            "filesize_bytes": file_size,
        }

        meta_created_at: datetime | None = None
        meta_modified_at: datetime | None = None
        author = ""
        software = ""
        device_make = ""
        device_model = ""

        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                raw_dict["dimensions"] = {"width": img.width, "height": img.height}
                raw_dict["mode"] = img.mode

                exif = img.getexif()
                if exif:
                    exif_data = {}
                    for tag_id, val in exif.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        # Convert bytes or un-serializable objects to string
                        if isinstance(val, bytes):
                            val_str = val.decode("utf-8", errors="replace").strip()
                        else:
                            val_str = str(val).strip()
                        exif_data[tag_name] = val_str

                    raw_dict["exif"] = exif_data

                    software = exif_data.get("Software", "")
                    device_make = exif_data.get("Make", "")
                    device_model = exif_data.get("Model", "")
                    author = exif_data.get("Artist", "") or exif_data.get("Copyright", "")

                    # Timestamps
                    date_orig = exif_data.get("DateTimeOriginal") or exif_data.get(
                        "DateTimeDigitized"
                    )
                    date_mod = exif_data.get("DateTime")

                    if date_orig:
                        meta_created_at = cls._parse_exif_date(date_orig)
                    if date_mod:
                        meta_modified_at = cls._parse_exif_date(date_mod)

                # Check XMP metadata if PNG or TIFF
                if hasattr(img, "info") and img.info:
                    raw_dict["image_info"] = {
                        k: str(v)[:200] for k, v in img.info.items() if k != "exif"
                    }
                    if not software and "Software" in img.info:
                        software = str(img.info["Software"])

        except Exception as e:
            logger.warning("Error parsing image metadata for {}: {}", filename, e)
            raw_dict["parser_error"] = str(e)

        device_str = f"{device_make} {device_model}".strip()
        final_software = software or (f"Camera: {device_str}" if device_str else "Unknown")

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
            meta_creator=device_str,
            meta_software=final_software,
            raw_dict=raw_dict,
        )

    @staticmethod
    def _parse_exif_date(date_str: str) -> datetime | None:
        if not date_str:
            return None
        # Format: "YYYY:MM:DD HH:MM:SS"
        try:
            clean_str = date_str.strip()
            if ":" in clean_str[:10]:
                parts = clean_str.split(" ", 1)
                date_part = parts[0].replace(":", "-")
                time_part = parts[1] if len(parts) > 1 else "00:00:00"
                clean_str = f"{date_part}T{time_part}"

            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except Exception as e:
            logger.debug("Failed parsing EXIF date {}: {}", date_str, e)
            return None
