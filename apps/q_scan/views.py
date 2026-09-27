"""
Q-Scan Views (Thin Presentation Layer)
Routes requests, validates parameters, and coordinates selectors & services.
"""

import csv
import json
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .selectors import (
    get_all_scanned_devices,
    get_evidence_hits_query,
    get_scan_dashboard_metrics,
    get_scanned_device_by_id,
)
from .services import (
    delete_scanned_device,
    ingest_scan_csv_file,
    update_evidence_hit_review,
)


def scan_dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Main Q-Scan forensic dashboard displaying audited endpoints, keyword metrics,
    and interactive Tabulator evidence grid.
    """
    selected_device_id = request.GET.get("device_id", "").strip()
    selected_keyword = request.GET.get("keyword", "").strip()
    selected_match_type = request.GET.get("match_type", "").strip()
    search_query = request.GET.get("q", "").strip()

    # Fetch metrics & devices
    metrics = get_scan_dashboard_metrics()
    devices = get_all_scanned_devices()

    # Query hits
    hits = get_evidence_hits_query(
        device_id=selected_device_id or None,
        keyword=selected_keyword or None,
        match_type=selected_match_type or None,
        search_query=search_query or None,
    )

    # Format table data for Tabulator
    table_data = []
    for h in hits[:1000]:  # Cap initial table payload at 1000 for instant UI rendering
        table_data.append(
            {
                "id": str(h.id),
                "hostname": h.device.hostname,
                "file_path": h.file_path,
                "filename": h.filename,
                "extension": h.extension,
                "file_size_bytes": h.file_size_bytes,
                "file_size_display": _format_size(h.file_size_bytes),
                "matched_keyword": h.matched_keyword,
                "match_type": h.match_type,
                "match_type_label": h.get_match_type_display(),
                "snippet": h.snippet or "-",
                "risk_score": h.risk_score,
                "file_modified_at": (
                    h.file_modified_at.strftime("%Y-%m-%d %H:%M") if h.file_modified_at else "-"
                ),
                "detection_timestamp": (
                    h.detection_timestamp.strftime("%Y-%m-%d %H:%M")
                    if h.detection_timestamp
                    else "-"
                ),
                "is_reviewed": h.is_reviewed,
            }
        )

    context = {
        "metrics": metrics,
        "devices": devices,
        "selected_device_id": selected_device_id,
        "selected_keyword": selected_keyword,
        "selected_match_type": selected_match_type,
        "search_query": search_query,
        "table_data_json": json.dumps(table_data),
        "total_filtered_hits": hits.count(),
    }
    return render(request, "q_scan/dashboard.html", context)


@require_POST
def upload_scan_csv_view(request: HttpRequest) -> HttpResponse:
    """
    Receives and processes uploaded scan_results.csv files from field auditors.
    """
    if "csv_file" not in request.FILES:
        messages.error(request, "No CSV file provided. Please select a scan_results.csv file.")
        return redirect("q_scan:dashboard")

    uploaded_file = request.FILES["csv_file"]
    hostname = request.POST.get("hostname", "").strip() or Path(uploaded_file.name).stem.upper()
    scan_title = request.POST.get("scan_title", "").strip() or "Audited Endpoint Scan"
    custodian_name = request.POST.get("custodian_name", "").strip()
    drive_letter = request.POST.get("drive_letter", "C:\\").strip()

    try:
        device = ingest_scan_csv_file(
            csv_file_obj_or_path=uploaded_file,
            hostname=hostname,
            scan_title=scan_title,
            custodian_name=custodian_name,
            drive_letter=drive_letter,
        )
        messages.success(
            request,
            f"Successfully imported {device.total_matches_found:,} evidence hits from '{device.hostname}'.",
        )
    except Exception as e:
        messages.error(request, f"Failed to parse and import CSV file: {e}")

    return redirect("q_scan:dashboard")


@require_http_methods(["GET", "POST"])
def device_detail_view(request: HttpRequest, device_id: str) -> HttpResponse:
    """
    Displays deep-dive details and hits for a specific scanned device.
    """
    device = get_scanned_device_by_id(device_id)
    if not device:
        raise Http404("Scanned device not found")

    hits = get_evidence_hits_query(device_id=device.id)

    table_data = [
        {
            "id": str(h.id),
            "hostname": device.hostname,
            "file_path": h.file_path,
            "filename": h.filename,
            "extension": h.extension,
            "file_size_bytes": h.file_size_bytes,
            "file_size_display": _format_size(h.file_size_bytes),
            "matched_keyword": h.matched_keyword,
            "match_type": h.match_type,
            "match_type_label": h.get_match_type_display(),
            "snippet": h.snippet or "-",
            "risk_score": h.risk_score,
            "file_modified_at": (
                h.file_modified_at.strftime("%Y-%m-%d %H:%M") if h.file_modified_at else "-"
            ),
            "detection_timestamp": (
                h.detection_timestamp.strftime("%Y-%m-%d %H:%M") if h.detection_timestamp else "-"
            ),
            "is_reviewed": h.is_reviewed,
        }
        for h in hits
    ]

    return render(
        request,
        "q_scan/device_detail.html",
        {
            "device": device,
            "table_data_json": json.dumps(table_data),
            "total_hits": hits.count(),
        },
    )


@require_POST
def delete_device_view(request: HttpRequest, device_id: str) -> HttpResponse:
    """
    Deletes a device audit case and cascades to its evidence hits.
    """
    success = delete_scanned_device(device_id)
    if success:
        messages.success(request, "Endpoint scan case deleted successfully.")
    else:
        messages.error(request, "Target endpoint case could not be found.")
    return redirect("q_scan:dashboard")


@require_POST
def review_hit_api_view(request: HttpRequest, hit_id: str) -> JsonResponse:
    """
    AJAX endpoint to update analyst review status and notes on a hit.
    """
    try:
        data = json.loads(request.body)
        is_reviewed = bool(data.get("is_reviewed", True))
        reviewer_notes = str(data.get("reviewer_notes", ""))
        hit = update_evidence_hit_review(
            hit_id, is_reviewed=is_reviewed, reviewer_notes=reviewer_notes
        )
        if hit:
            return JsonResponse({"status": "ok", "is_reviewed": hit.is_reviewed})
        return JsonResponse({"status": "error", "message": "Hit not found"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


def export_hits_csv_view(request: HttpRequest) -> HttpResponse:
    """
    Exports filtered evidence hits to a downloadable CSV file.
    """
    selected_device_id = request.GET.get("device_id", "").strip()
    selected_keyword = request.GET.get("keyword", "").strip()
    selected_match_type = request.GET.get("match_type", "").strip()

    hits = get_evidence_hits_query(
        device_id=selected_device_id or None,
        keyword=selected_keyword or None,
        match_type=selected_match_type or None,
    )

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="forensiq_scan_export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Hostname",
            "File Path",
            "Filename",
            "Matched Keyword",
            "Match Type",
            "Risk Score",
            "File Size (Bytes)",
            "Last Modified Date",
            "Detection Time",
            "Snippet / Context",
        ]
    )

    for h in hits:
        writer.writerow(
            [
                h.device.hostname,
                h.file_path,
                h.filename,
                h.matched_keyword,
                h.match_type,
                h.risk_score,
                h.file_size_bytes,
                h.file_modified_at.strftime("%Y-%m-%d %H:%M:%S") if h.file_modified_at else "",
                h.detection_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                if h.detection_timestamp
                else "",
                h.snippet,
            ]
        )

    return response


def download_tool_file_view(request: HttpRequest, filename: str) -> HttpResponse:
    """
    Serves portable scanner scripts (q_scan.py, config.json, build_exe.bat) to field auditors.
    """
    allowed_files = {
        "q_scan.exe": settings.BASE_DIR / "tools" / "q_scan" / "q_scan.exe",
        "q_scan_package.zip": settings.BASE_DIR / "tools" / "q_scan" / "q_scan_package.zip",
        "q_scan.py": settings.BASE_DIR / "tools" / "q_scan" / "q_scan.py",
        "config.json": settings.BASE_DIR / "tools" / "q_scan" / "config.json",
        "build_exe.bat": settings.BASE_DIR / "tools" / "q_scan" / "build_exe.bat",
        "build_exe.ps1": settings.BASE_DIR / "tools" / "q_scan" / "build_exe.ps1",
    }

    target_path = allowed_files.get(filename)
    if not target_path or not target_path.exists():
        raise Http404("Requested tool file not found")

    return FileResponse(open(target_path, "rb"), as_attachment=True, filename=filename)


def _format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"
