"""
Q-Ledger Views (Thin Presentation Layer)
Coordinates ERP evidence ingestion, interactive vendor filtering, and forensic audit presentation.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods
from loguru import logger

from .selectors import (
    get_active_dataset,
    get_checkpoint_tables,
    get_export_dataframe,
    get_filtered_dataset,
    get_ledger_charts,
    get_ledger_kpis,
    get_master_config,
    get_top_rankings,
    get_vendor_list,
)
from .services import (
    ensure_masters_initialized,
    ingest_ledger_datasets,
    ingest_master_files,
    reset_ledger_cache,
)


@csrf_protect
@require_http_methods(["GET", "POST"])
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Main Q-Ledger Forensic Investigation Dashboard.
    Provides standard ForensiQ page header, KPI cards, visual charts, and 7 forensic checkpoints.
    """
    master_config = ensure_masters_initialized()

    context: dict = {
        "vendor_list": [],
        "selected_vendor": "",
        "record_count": 0,
        "master_config": master_config,
        "gl_account_count": master_config.gl_account_count if master_config else 0,
        "sloc_count": master_config.sloc_count if master_config else 0,
    }

    try:
        if request.method == "POST":
            action = request.POST.get("action", "")

            # 1. Master Excel Reference Upload (GL / SLoc)
            if (
                action == "upload_masters"
                or "gl_file" in request.FILES
                or "sloc_file" in request.FILES
            ):
                gl_file = request.FILES.get("gl_file")
                sloc_file = request.FILES.get("sloc_file")
                gl_cnt, sloc_cnt = ingest_master_files(gl_file=gl_file, sloc_file=sloc_file)
                context["message_success"] = (
                    f"Successfully stored GL Account ({gl_cnt:,}) and SLoc ({sloc_cnt:,}) "
                    "master files in the background."
                )

            # 2. Transactional SAP PR/PO & MARA Evidence Upload
            elif (
                action == "upload" or "prpo_file" in request.FILES or "prpo_files" in request.FILES
            ):
                prpo_files = request.FILES.getlist("prpo_file") or request.FILES.getlist(
                    "prpo_files"
                )
                mara_files = request.FILES.getlist("mara_file") or request.FILES.getlist(
                    "mara_files"
                )
                _, record_count = ingest_ledger_datasets(
                    prpo_files=prpo_files, mara_files=mara_files
                )
                if record_count > 0:
                    request.session["selected_vendor"] = ""
                    context["message_success"] = (
                        f"Successfully ingested and stored {record_count:,} SAP records in the backend."
                    )
                else:
                    context["message_error"] = (
                        "Failed to parse PR/PO records. Please verify file structure."
                    )

            # 3. Vendor Filter Drilldown
            elif "vendor_filter" in request.POST:
                selected_vendor = request.POST.get("vendor_filter", "").strip()
                request.session["selected_vendor"] = selected_vendor

        # Retrieve Active Datasets via Selector
        df, df2 = get_active_dataset()

        if df is not None and not df.empty:
            context["vendor_list"] = get_vendor_list(df)

            selected_vendor = request.session.get("selected_vendor", "")
            context["selected_vendor"] = selected_vendor
            context["is_vendor_filtered"] = bool(selected_vendor)

            filtered_df = get_filtered_dataset(df, selected_vendor)
            context["record_count"] = len(filtered_df) if filtered_df is not None else 0

            # Forensic KPIs
            context.update(get_ledger_kpis(filtered_df))

            # Top Rankings
            context.update(get_top_rankings(filtered_df, selected_vendor))

            # Plotly Charts
            context.update(get_ledger_charts(filtered_df))

            # Forensic Checkpoints
            context.update(get_checkpoint_tables(filtered_df, df2))

    except Exception as ex:
        logger.error("Error in Q-Ledger dashboard view: {}", ex)
        context["message_error"] = str(ex)

    # Refresh master counts after any potential updates
    active_config = get_master_config()
    if active_config:
        context["master_config"] = active_config
        context["gl_account_count"] = active_config.gl_account_count
        context["sloc_count"] = active_config.sloc_count

    return render(request, "q_ledger/dashboard.html", context)


@require_GET
def export_current_view(request: HttpRequest) -> HttpResponse:
    """
    Exports the current filtered dataset as an Excel spreadsheet (.xlsx).
    """
    selected_vendor = request.session.get("selected_vendor", "")
    df, filename = get_export_dataframe(selected_vendor)

    if df is None or df.empty:
        return HttpResponse("No filtered data available for export.", status=404)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    df.to_excel(response, index=False, engine="openpyxl")
    return response


@require_GET
def reset_data_view(request: HttpRequest) -> HttpResponse:
    """
    Resets the active dataset cache back to default seed state.
    """
    request.session["selected_vendor"] = ""
    reset_ledger_cache()
    return redirect("/ledger/")
