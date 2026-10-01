"""
Q-Voice Forensic Selectors
Queries, aggregates, and computes statistics for voice call recordings, speaker talk-time, and timeline segments.
"""

import uuid
from typing import Any

from django.db.models import Count, QuerySet, Sum

from .backend.voice_parser import tag_transcript_detections
from .models import AudioRecording, TranscriptSegment


def get_all_recordings() -> QuerySet[AudioRecording]:
    """
    Retrieves all audio recordings ordered by timestamp.
    """
    return AudioRecording.objects.all().order_by("-call_timestamp", "-created_at")


def get_recording_by_id(recording_id: str | uuid.UUID) -> AudioRecording | None:
    """
    Retrieves a single audio recording with prefetched segments.
    """
    try:
        return AudioRecording.objects.prefetch_related("segments").get(id=recording_id)
    except (AudioRecording.DoesNotExist, ValueError):
        return None


def get_latest_completed_recording() -> AudioRecording | None:
    """
    Returns the most recent completed recording.
    """
    return (
        AudioRecording.objects.filter(
            transcription_status=AudioRecording.TranscriptionStatus.COMPLETED
        )
        .prefetch_related("segments")
        .first()
    )


def get_combined_timeline_for_recording(recording: AudioRecording) -> list[dict[str, Any]]:
    """
    Builds the standardized combined timeline format for the active recording.
    """
    segments = recording.segments.all().order_by("start_time_seconds", "created_at")
    timeline: list[dict[str, Any]] = []

    for seg in segments:
        s_sec = int(seg.start_time_seconds)
        e_sec = int(seg.end_time_seconds)
        s_fmt = f"{s_sec // 3600:02d}:{(s_sec % 3600) // 60:02d}:{s_sec % 60:02d}"
        e_fmt = f"{e_sec // 3600:02d}:{(e_sec % 3600) // 60:02d}:{e_sec % 60:02d}"
        ts_label = f"[{s_fmt} --> {e_fmt}]"

        # Detections detail with tag classifications
        detections_detail = tag_transcript_detections(seg.text_content)

        timeline.append(
            {
                "timestamp": ts_label,
                "start_seconds": seg.start_time_seconds,
                "end_seconds": seg.end_time_seconds,
                "speaker": seg.speaker_tag or "Speaker",
                "transcript": seg.text_content,
                "detected_intent": seg.detected_intent or "General",
                "risk_score": seg.risk_score,
                "detections": seg.flagged_keywords or [d["term"] for d in detections_detail],
                "detections_detail": detections_detail,
            }
        )

    return timeline


def get_metrics_for_recording(recording: AudioRecording) -> dict[str, Any]:
    """
    Calculates HUD metrics (identities, financial terms, suspicious parameters) for an active recording.
    """
    timeline = get_combined_timeline_for_recording(recording)
    identities_cnt = 0
    financial_cnt = 0
    suspicious_cnt = 0

    for item in timeline:
        for det in item["detections_detail"]:
            t = det.get("type", "")
            if t == "identity":
                identities_cnt += 1
            elif t == "financial":
                financial_cnt += 1
            elif t == "suspicious":
                suspicious_cnt += 1

    mins, secs = divmod(recording.duration_seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        duration_fmt = f"{hrs:02d}h {mins:02d}m {secs:02d}s"
    else:
        duration_fmt = f"{mins:02d}m {secs:02d}s"

    return {
        "identities_count": identities_cnt,
        "financial_count": financial_cnt,
        "suspicious_count": suspicious_cnt,
        "total_segments": len(timeline),
        "duration_formatted": duration_fmt,
        "risk_score": recording.risk_score,
    }


def get_global_voice_metrics() -> dict[str, Any]:
    """
    Computes global metrics across all ingested audio recordings in the system.
    """
    total_recordings = AudioRecording.objects.count()
    duration_sum = (
        AudioRecording.objects.aggregate(total_sec=Sum("duration_seconds"))["total_sec"] or 0
    )
    total_segments = TranscriptSegment.objects.count()
    flagged_segments = TranscriptSegment.objects.filter(risk_score__gte=50).count()
    collusion_calls = (
        AudioRecording.objects.filter(segments__detected_intent="Collusion").distinct().count()
    )

    hrs, remainder = divmod(duration_sum, 3600)
    mins, secs = divmod(remainder, 60)
    duration_fmt = f"{hrs}h {mins}m {secs}s" if hrs > 0 else f"{mins}m {secs}s"

    intent_breakdown = list(
        TranscriptSegment.objects.values("detected_intent")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return {
        "total_recordings": total_recordings,
        "total_duration_seconds": duration_sum,
        "total_duration_formatted": duration_fmt,
        "total_segments": total_segments,
        "flagged_segments": flagged_segments,
        "collusion_calls": collusion_calls,
        "intent_breakdown": intent_breakdown,
    }
