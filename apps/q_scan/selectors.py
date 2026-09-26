"""
Q-Scan Selectors (Read-Only Queries)
Optimized, N+1 safe queries for dashboards, Tabulator data tables, and metrics aggregations.
"""

import uuid
from typing import Any

from django.db.models import Count, Q, QuerySet

from .models import FileEvidenceHit, ScannedDevice


def get_all_scanned_devices() -> QuerySet[ScannedDevice]:
    """
    Fetches all audited endpoint devices ordered by latest scan.
    """
    return ScannedDevice.objects.annotate(actual_hit_count=Count("hits")).order_by("-created_at")


def get_scanned_device_by_id(device_id: str | uuid.UUID) -> ScannedDevice | None:
    """
    Retrieves a single scanned device by primary key.
    """
    try:
        return ScannedDevice.objects.get(id=device_id)
    except (ScannedDevice.DoesNotExist, ValueError):
        return None


def get_evidence_hits_query(
    *,
    device_id: str | uuid.UUID | None = None,
    keyword: str | None = None,
    match_type: str | None = None,
    search_query: str | None = None,
) -> QuerySet[FileEvidenceHit]:
    """
    Retrieves evidence hits with proactive select_related('device') to eliminate N+1 queries.
    """
    qs = FileEvidenceHit.objects.select_related("device").all()

    if device_id:
        qs = qs.filter(device_id=device_id)

    if keyword:
        qs = qs.filter(matched_keyword__iexact=keyword.strip())

    if match_type:
        qs = qs.filter(match_type=match_type.strip())

    if search_query:
        q_str = search_query.strip()
        qs = qs.filter(
            Q(filename__icontains=q_str)
            | Q(file_path__icontains=q_str)
            | Q(matched_keyword__icontains=q_str)
            | Q(snippet__icontains=q_str)
            | Q(device__hostname__icontains=q_str)
        )

    return qs.order_by("-risk_score", "-created_at")


def get_scan_dashboard_metrics() -> dict[str, Any]:
    """
    Aggregates high-level forensic metrics across all endpoint scans.
    """
    total_devices = ScannedDevice.objects.count()
    total_hits = FileEvidenceHit.objects.count()
    high_risk_hits = FileEvidenceHit.objects.filter(risk_score__gte=70).count()
    reviewed_hits = FileEvidenceHit.objects.filter(is_reviewed=True).count()

    top_keywords_qs = (
        FileEvidenceHit.objects.values("matched_keyword")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )
    top_keywords = [
        {"keyword": item["matched_keyword"], "count": item["count"]} for item in top_keywords_qs
    ]

    match_types_qs = (
        FileEvidenceHit.objects.values("match_type").annotate(count=Count("id")).order_by("-count")
    )
    match_types = [{"type": item["match_type"], "count": item["count"]} for item in match_types_qs]

    return {
        "total_devices": total_devices,
        "total_hits": total_hits,
        "high_risk_hits": high_risk_hits,
        "reviewed_hits": reviewed_hits,
        "top_keywords": top_keywords,
        "match_types": match_types,
    }


def get_top_matched_keywords(limit: int = 10) -> list[dict[str, Any]]:
    """
    Returns the most frequently matched forensic keywords.
    """
    qs = (
        FileEvidenceHit.objects.values("matched_keyword")
        .annotate(hit_count=Count("id"))
        .order_by("-hit_count")[:limit]
    )
    return list(qs)
