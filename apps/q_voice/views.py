"""
Q-Voice Forensic Views
Provides a common audios directory dashboard and individual recording dossiers, matching the Q-Bank architecture.
"""

import json
import uuid
from typing import Any

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from core.profiles import resolve_or_create_profile_from_request

from .models import AudioRecording
from .selectors import (
    get_all_recordings,
    get_combined_timeline_for_recording,
    get_global_voice_metrics,
    get_metrics_for_recording,
    get_recording_by_id,
)
from .services import (
    delete_audio_recording,
    get_voice_api_endpoint,
    ingest_audio_recording,
)


def dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Common Q-Voice Hub & Case Directory Dashboard.
    Displays global platform metrics and the directory of all ingested voice call cases.
    """
    context: dict[str, Any] = {
        "status": "idle",
        "recordings": get_all_recordings(),
        "global_metrics": get_global_voice_metrics(),
        "error_message": "",
        "voice_endpoint": get_voice_api_endpoint(),
    }

    # Handle file upload from modal on common dashboard
    if request.method == "POST":
        audio_file = request.FILES.get("audio_file")
        if not audio_file:
            context["error_message"] = "No audio file provided. Please choose a .wav or .mp3 file."
            context["status"] = "error"
        else:
            call_ref = request.POST.get("call_ref", "")
            call_title = request.POST.get("call_title", "")
            _profile, resolved_name = resolve_or_create_profile_from_request(
                request, default_department="Strategic Sourcing"
            )
            custodian_name = (
                resolved_name or request.POST.get("custodian_name", "").strip() or "Target Auditee"
            )

            recording, error_msg = ingest_audio_recording(
                audio_file=audio_file,
                call_ref=call_ref,
                call_title=call_title,
                custodian_name=custodian_name,
            )

            if (
                error_msg
                or not recording
                or recording.transcription_status == AudioRecording.TranscriptionStatus.FAILED
            ):
                context["error_message"] = (
                    error_msg or "Local transcription service failed to process audio."
                )
                context["status"] = "error"
            else:
                messages.success(
                    request, f"Transcription completed successfully: {recording.call_ref}"
                )
                return redirect("q_voice:recording_detail", recording_id=recording.id)

    return render(request, "q_voice/dashboard.html", context)


def recording_detail_view(request: HttpRequest, recording_id: uuid.UUID) -> HttpResponse:
    """
    Individual Audio Case Forensic Dossier View.
    Displays interactive horizontal timeline, forensic hotwords, and verbatim speech transcripts for a single recording.
    """
    recording = get_recording_by_id(recording_id)
    if not recording:
        raise Http404(f"Voice recording '{recording_id}' not found.")

    timeline = get_combined_timeline_for_recording(recording)
    metrics = get_metrics_for_recording(recording)

    # Prepare JSON string for client-side horizontal interactive timeline
    clean_json_timeline = [
        {
            "timestamp": item["timestamp"],
            "start_seconds": item["start_seconds"],
            "end_seconds": item["end_seconds"],
            "transcript": item["transcript"],
            "speaker": item["speaker"],
            "detections": item["detections"],
            "detections_detail": item["detections_detail"],
        }
        for item in timeline
    ]

    context: dict[str, Any] = {
        "recording": recording,
        "combined_timeline": timeline,
        "metrics": metrics,
        "timeline_json": json.dumps(clean_json_timeline),
        "all_recordings": get_all_recordings(),
        "voice_endpoint": get_voice_api_endpoint(),
    }

    return render(request, "q_voice/recording_detail.html", context)


def delete_recording_view(request: HttpRequest, recording_id: uuid.UUID) -> HttpResponse:
    """
    Deletes an audio recording and returns to the common voice dashboard.
    """
    success = delete_audio_recording(recording_id)
    if success:
        messages.success(request, "Audio recording and acoustic dossier successfully removed.")
    else:
        messages.error(request, "Audio recording could not be found.")

    return redirect("q_voice:dashboard")
