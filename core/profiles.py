"""
Core Investigation Profiles Service & Selectors
Provides unified profile management, cross-app profile resolution, and synchronization.
"""

import uuid

from django.db.models import QuerySet
from django.http import HttpRequest
from loguru import logger

from .models import InvestigationProfile


def get_all_profiles() -> QuerySet[InvestigationProfile]:
    """
    Returns all investigation profiles ordered by full name.
    """
    return InvestigationProfile.objects.all().order_by("full_name")


def get_profile_by_id(profile_id: str | uuid.UUID | None) -> InvestigationProfile | None:
    """
    Retrieves an investigation profile by ID.
    """
    if not profile_id:
        return None
    try:
        return InvestigationProfile.objects.filter(id=profile_id).first()
    except (ValueError, TypeError):
        return None


def get_active_profile(request: HttpRequest) -> InvestigationProfile | None:
    """
    Returns the currently active profile selected in the user's session.
    """
    active_id = request.session.get("active_profile_id")
    if active_id:
        profile = get_profile_by_id(active_id)
        if profile:
            return profile
    return None


def set_active_profile(
    request: HttpRequest, profile_id: str | uuid.UUID | None
) -> InvestigationProfile | None:
    """
    Sets the active profile in the session.
    """
    if not profile_id:
        request.session.pop("active_profile_id", None)
        request.session.modified = True
        return None

    profile = get_profile_by_id(profile_id)
    if profile:
        request.session["active_profile_id"] = str(profile.id)
        request.session["active_profile_name"] = profile.full_name
        request.session.modified = True
        return profile

    return None


def create_investigation_profile(
    *,
    full_name: str,
    employee_id: str = "",
    department: str = "",
    designation: str = "",
    email: str = "",
    phone: str = "",
    risk_level: str = "MEDIUM",
    status: str = "ACTIVE",
    notes: str = "",
    avatar_color: str = "indigo",
) -> InvestigationProfile:
    """
    Creates a new unified investigation profile and synchronizes it across modules.
    """
    clean_name = full_name.strip()
    if not clean_name:
        raise ValueError("Profile full name cannot be blank.")

    profile = InvestigationProfile.objects.create(
        full_name=clean_name,
        employee_id=employee_id.strip(),
        department=department.strip(),
        designation=designation.strip(),
        email=email.strip().lower(),
        phone=phone.strip(),
        risk_level=risk_level
        if risk_level in dict(InvestigationProfile.RiskLevel.choices)
        else "MEDIUM",
        status=status if status in dict(InvestigationProfile.Status.choices) else "ACTIVE",
        notes=notes.strip(),
        avatar_color=avatar_color.strip() or "indigo",
    )

    # Sync to Q-Bank AuditedPerson if q_bank is available
    try:
        from q_bank.models import AuditedPerson

        AuditedPerson.objects.get_or_create(
            full_name=profile.full_name,
            defaults={
                "employee_id": profile.employee_id,
                "department": profile.department,
                "designation": profile.designation,
                "email": profile.email,
                "phone": profile.phone,
                "notes": profile.notes,
            },
        )
    except Exception as exc:
        logger.debug(f"Optional Q-Bank sync skipped: {exc}")

    return profile


def resolve_or_create_profile_from_request(
    request: HttpRequest,
    *,
    default_department: str = "",
) -> tuple[InvestigationProfile | None, str]:
    """
    Resolves an existing profile or creates a new one from incoming form POST parameters.
    Checks:
    1. 'profile_id' (UUID of existing profile)
    2. 'new_profile_name' (inline profile creation in modal)
    3. 'custodian_name' or 'account_holder' (fallback name fields)
    Returns: (InvestigationProfile or None, custodian_name_str)
    """
    profile_id = request.POST.get("profile_id", "").strip()
    new_profile_name = request.POST.get("new_profile_name", "").strip()
    new_profile_dept = request.POST.get("new_profile_dept", "").strip() or default_department
    new_profile_role = request.POST.get("new_profile_role", "").strip()

    # 1. Existing Profile Selected
    if profile_id and profile_id != "__new__":
        profile = get_profile_by_id(profile_id)
        if profile:
            # Set as active session profile
            request.session["active_profile_id"] = str(profile.id)
            request.session["active_profile_name"] = profile.full_name
            request.session.modified = True
            return profile, profile.full_name

    # 2. Inline New Profile Submitted
    if new_profile_name:
        existing = InvestigationProfile.objects.filter(full_name__iexact=new_profile_name).first()
        if existing:
            request.session["active_profile_id"] = str(existing.id)
            request.session.modified = True
            return existing, existing.full_name

        profile = create_investigation_profile(
            full_name=new_profile_name,
            department=new_profile_dept,
            designation=new_profile_role,
        )
        request.session["active_profile_id"] = str(profile.id)
        request.session.modified = True
        return profile, profile.full_name

    # 3. Fallback standard custodian input (e.g. custodian_name or account_holder)
    legacy_name = (
        request.POST.get("custodian_name", "").strip()
        or request.POST.get("account_holder", "").strip()
        or request.POST.get("target_name", "").strip()
    )
    if legacy_name:
        existing = InvestigationProfile.objects.filter(full_name__iexact=legacy_name).first()
        if existing:
            return existing, existing.full_name

        profile = create_investigation_profile(
            full_name=legacy_name,
            department=default_department,
        )
        return profile, profile.full_name

    # 4. Check active session profile if available
    active_profile = get_active_profile(request)
    if active_profile:
        return active_profile, active_profile.full_name

    return None, ""


def sync_all_existing_entities_to_profiles() -> int:
    """
    One-time synchronization that scans historical records across modules
    (Q-Bank, Q-Voice, Q-Verify) and ensures corresponding InvestigationProfiles exist.
    Returns the number of newly created profiles.
    """
    created_count = 0

    # 1. Sync from Q-Bank AuditedPerson
    try:
        from q_bank.models import AuditedPerson

        for person in AuditedPerson.objects.all():
            clean_name = person.full_name.replace("(Auditee)", "").strip()
            if not clean_name:
                continue
            if not InvestigationProfile.objects.filter(full_name__iexact=clean_name).exists():
                InvestigationProfile.objects.create(
                    full_name=clean_name,
                    employee_id=person.employee_id,
                    department=person.department or "Procurement",
                    designation=person.designation or "Target Auditee",
                    email=person.email,
                    phone=person.phone,
                    notes=person.notes,
                    risk_level="HIGH" if "flagged" in person.notes.lower() else "MEDIUM",
                    avatar_color="orange",
                )
                created_count += 1
    except Exception as exc:
        logger.debug(f"Sync from Q-Bank skipped: {exc}")

    # 2. Sync from Q-Voice AudioRecording
    try:
        from q_voice.models import AudioRecording

        for rec in AudioRecording.objects.all():
            name = (rec.custodian_name or "").strip()
            if not name or name.lower() in ("target auditee", "unknown"):
                continue
            if not InvestigationProfile.objects.filter(full_name__iexact=name).exists():
                InvestigationProfile.objects.create(
                    full_name=name,
                    department="Strategic Sourcing & Logistics",
                    designation="Intercept Subject",
                    avatar_color="indigo",
                    risk_level="HIGH" if rec.risk_score >= 50 else "MEDIUM",
                )
                created_count += 1
    except Exception as exc:
        logger.debug(f"Sync from Q-Voice skipped: {exc}")

    # 3. Sync from Q-Verify VerificationCase
    try:
        from q_verify.models import VerificationCase

        for case in VerificationCase.objects.all():
            name = (case.custodian_name or "").strip()
            if not name or name.lower() in ("target custodian", "unknown"):
                continue
            if not InvestigationProfile.objects.filter(full_name__iexact=name).exists():
                InvestigationProfile.objects.create(
                    full_name=name,
                    department=case.custodian_department or "Procurement",
                    email=case.custodian_email,
                    avatar_color="rose",
                )
                created_count += 1
    except Exception as exc:
        logger.debug(f"Sync from Q-Verify skipped: {exc}")

    return created_count
