"""
Core Context Processors
Injects global forensic workstation data, such as investigation profiles and session state.
"""

from typing import Any

from django.http import HttpRequest

from .profiles import (
    get_active_profile,
    get_all_profiles,
    sync_all_existing_entities_to_profiles,
)


def global_profiles_context(request: HttpRequest) -> dict[str, Any]:
    """
    Supplies investigation profiles and active profile to all templates across the workstation.
    """
    try:
        profiles = list(get_all_profiles())
        if not profiles:
            sync_all_existing_entities_to_profiles()
            profiles = list(get_all_profiles())

        active = get_active_profile(request)
        if not active and profiles:
            # Fallback to the first active profile if none explicitly selected in session
            active = profiles[0]

        return {
            "investigation_profiles": profiles,
            "active_profile": active,
            "total_profiles_count": len(profiles),
        }
    except Exception:
        return {
            "investigation_profiles": [],
            "active_profile": None,
            "total_profiles_count": 0,
        }
