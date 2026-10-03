import json
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .modules import get_discovered_modules
from .profiles import (
    add_keywords_to_profile,
    create_investigation_profile,
    extract_keywords_from_file,
    get_all_profiles,
    set_active_profile,
)


@csrf_protect
def portal_login_view(request):
    """
    Master Portal Password Login View.
    Authenticates investigative access using only a portal password key.
    """
    next_url = request.GET.get("next") or request.POST.get("next") or "/"

    # Sanitize next_url against open redirect
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/"

    # If already logged in, redirect straight away
    if request.session.get("portal_authenticated", False):
        return redirect(next_url)

    error = None

    if request.method == "POST":
        password = request.POST.get("password", "").strip()
        expected_password = getattr(settings, "PORTAL_ACCESS_PASSWORD", "")

        if password and expected_password and password == expected_password:
            request.session["portal_authenticated"] = True
            request.session.modified = True
            return redirect(next_url)
        else:
            error = "Invalid portal access key. Please verify your credentials."

    return render(
        request,
        "core/login.html",
        {
            "error": error,
            "next": next_url,
        },
    )


def portal_logout_view(request):
    """
    Logout View to lock the workstation and clear session credentials.
    """
    request.session.flush()
    return redirect("/login/")


def landing_view(request: HttpRequest) -> HttpResponse:
    """
    ForensiQ Landing Page dynamically loading all modules from apps/ directory
    and registered investigation profiles with their surveillance keywords.
    """
    modules = get_discovered_modules()
    profiles = [p.to_dict() for p in get_all_profiles()]
    return render(
        request,
        "core/landing.html",
        {
            "modules": modules,
            "total_modules": len(modules),
            "profiles": profiles,
            "profiles_json": json.dumps(profiles),
        },
    )


@require_POST
def create_profile_view(request: HttpRequest) -> HttpResponse:
    """
    Creates a new investigation profile with optional surveillance keywords
    from modal submission or AJAX fetch.
    """
    is_json = (
        request.content_type == "application/json"
        or request.headers.get("x-requested-with") == "XMLHttpRequest"
    )
    if is_json and request.body:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            payload = {}
    else:
        payload = request.POST

    full_name = payload.get("full_name", "").strip()
    if not full_name:
        if is_json:
            return JsonResponse(
                {"status": "error", "message": "Target name is required."}, status=400
            )
        messages.error(request, "Target profile full name is required.")
        return redirect(payload.get("next", "/"))

    keywords_input = payload.get("keywords")
    if not keywords_input and not is_json:
        # Also check comma-separated keywords string from form post
        keywords_input = request.POST.get("keywords_input", "")

    profile = create_investigation_profile(
        full_name=full_name,
        employee_id=payload.get("employee_id", "").strip(),
        department=payload.get("department", "").strip(),
        designation=payload.get("designation", "").strip(),
        email=payload.get("email", "").strip(),
        phone=payload.get("phone", "").strip(),
        risk_level=payload.get("risk_level", "MEDIUM").strip() or "MEDIUM",
        notes=payload.get("notes", "").strip(),
        avatar_color=payload.get("avatar_color", "indigo").strip() or "indigo",
        keywords=keywords_input,
    )

    # Automatically set newly created profile as active in session
    set_active_profile(request, profile.id)

    if is_json:
        return JsonResponse({"status": "success", "profile": profile.to_dict()})

    messages.success(
        request, f"Investigation Profile '{profile.full_name}' successfully registered."
    )
    next_url = payload.get("next") or "/"
    return redirect(next_url)


ALLOWED_KEYWORDS_EXTENSIONS = {".txt", ".csv", ".xlsx", ".xls"}
MAX_KEYWORDS_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@require_POST
def add_profile_keywords_view(request: HttpRequest, profile_id: str) -> JsonResponse:
    """
    Appends search and surveillance keywords to an existing investigation profile.
    """
    is_json = (
        request.content_type == "application/json"
        or request.headers.get("x-requested-with") == "XMLHttpRequest"
    )
    if is_json and request.body:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            payload = {}
    else:
        payload = request.POST

    keywords = payload.get("keywords")
    if not keywords:
        return JsonResponse(
            {"status": "error", "message": "At least one keyword is required."},
            status=400,
        )

    try:
        profile = add_keywords_to_profile(profile_id, keywords)
        return JsonResponse(
            {
                "status": "success",
                "message": f"Keywords appended to {profile.full_name}",
                "profile": profile.to_dict(),
            }
        )
    except ValueError as err:
        return JsonResponse({"status": "error", "message": str(err)}, status=404)
    except Exception as err:
        return JsonResponse({"status": "error", "message": str(err)}, status=500)


@require_POST
def parse_keywords_file_view(request: HttpRequest) -> JsonResponse:
    """
    Parses and extracts keywords from an uploaded file (.txt, .xlsx, .xls, .csv).
    Returns the extracted list of keywords for client-side tag insertion.
    """
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse(
            {
                "status": "error",
                "message": "No file uploaded. Please select a .txt or .xlsx file.",
            },
            status=400,
        )

    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in ALLOWED_KEYWORDS_EXTENSIONS:
        return JsonResponse(
            {
                "status": "error",
                "message": f"Unsupported file type '{ext}'. Allowed formats: .txt, .xlsx, .xls, .csv",
            },
            status=400,
        )

    if uploaded_file.size > MAX_KEYWORDS_FILE_SIZE:
        return JsonResponse(
            {"status": "error", "message": "File exceeds 10MB size limit."},
            status=400,
        )

    try:
        keywords = extract_keywords_from_file(uploaded_file, uploaded_file.name)
        return JsonResponse(
            {
                "status": "success",
                "filename": uploaded_file.name,
                "count": len(keywords),
                "keywords": keywords,
            }
        )
    except Exception as err:
        return JsonResponse(
            {"status": "error", "message": f"Failed parsing keywords file: {err}"},
            status=500,
        )


@require_POST
def upload_profile_keywords_file_view(request: HttpRequest, profile_id: str) -> JsonResponse:
    """
    Uploads a keywords file (.txt, .xlsx, .xls, .csv) and directly attaches
    extracted surveillance keywords to an existing profile.
    """
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse(
            {
                "status": "error",
                "message": "No file uploaded. Please select a .txt or .xlsx file.",
            },
            status=400,
        )

    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in ALLOWED_KEYWORDS_EXTENSIONS:
        return JsonResponse(
            {
                "status": "error",
                "message": f"Unsupported file type '{ext}'. Allowed formats: .txt, .xlsx, .xls, .csv",
            },
            status=400,
        )

    if uploaded_file.size > MAX_KEYWORDS_FILE_SIZE:
        return JsonResponse(
            {"status": "error", "message": "File exceeds 10MB size limit."},
            status=400,
        )

    try:
        keywords = extract_keywords_from_file(uploaded_file, uploaded_file.name)
        if not keywords:
            return JsonResponse(
                {"status": "error", "message": "No valid keywords found in the uploaded file."},
                status=400,
            )

        profile = add_keywords_to_profile(profile_id, keywords)
        return JsonResponse(
            {
                "status": "success",
                "message": f"Appended {len(keywords)} keywords from '{uploaded_file.name}' to {profile.full_name}.",
                "filename": uploaded_file.name,
                "added_count": len(keywords),
                "profile": profile.to_dict(),
            }
        )
    except ValueError as err:
        return JsonResponse({"status": "error", "message": str(err)}, status=404)
    except Exception as err:
        return JsonResponse(
            {"status": "error", "message": f"Failed uploading keywords: {err}"},
            status=500,
        )


@require_POST
def set_active_profile_view(request: HttpRequest) -> HttpResponse:
    """
    Switches or clears the active investigation profile for the current investigator session.
    """
    is_json = (
        request.content_type == "application/json"
        or request.headers.get("x-requested-with") == "XMLHttpRequest"
    )
    if is_json and request.body:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            payload = {}
    else:
        payload = request.POST

    profile_id = payload.get("profile_id", "").strip()
    profile = set_active_profile(request, profile_id if profile_id else None)

    if is_json:
        return JsonResponse(
            {
                "status": "success",
                "active_profile": profile.to_dict() if profile else None,
            }
        )

    next_url = payload.get("next") or request.META.get("HTTP_REFERER") or "/"
    return redirect(next_url)


def profile_list_api_view(request: HttpRequest) -> JsonResponse:
    """
    JSON API returning all registered investigation profiles for client-side dropdowns and selectors.
    """
    profiles = get_all_profiles()
    return JsonResponse(
        {
            "status": "success",
            "profiles": [p.to_dict() for p in profiles],
        }
    )
