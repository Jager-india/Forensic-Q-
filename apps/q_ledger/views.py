"""
Q-Ledger Views
Orchestrates ERP evidence ingestion, interactive filtering, and audit dashboard presentation.
"""

from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from loguru import logger

from .models import LedgerDataset, LedgerMasterConfig
from .selectors import prepare_table_dict
from .services.analysis_functions import (
    dif_mat3,
    ersa,
    indian_rupee_format,
    indir_mat,
    mater_list,
    openpo,
    process_data_t7,
    row2_c1,
    row2_c2,
    row2_c3,
    tab66,
)
from .services.data_preprocessing import (
    dfmain,
    process_data,
    process_mara_data,
)

BASE_DIR = Path(settings.BASE_DIR)
BACKEND_DATA_DIR = BASE_DIR / "apps" / "q_ledger" / "backend" / "data"
PERSISTENT_CACHE_DIR = Path(settings.MEDIA_ROOT) / "q_ledger_cache"
PERSISTENT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
MASTERS_DIR = Path(settings.MEDIA_ROOT) / "q_ledger" / "masters"
MASTERS_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_masters_initialized() -> LedgerMasterConfig:
    """
    Ensures GL Account and SLoc master reference files are stored in the background.
    """
    config = LedgerMasterConfig.objects.filter(is_active=True).first()
    if config:
        return config

    fallback_gl = (
        BASE_DIR / "apps" / "q_ledger" / "assets" / "GL Acct Data" / "GL account list.xlsx"
    )
    fallback_sloc = BASE_DIR / "apps" / "q_ledger" / "assets" / "SLoc Desc" / "Sloc Desc.xlsx"

    gl_count = 0
    sloc_count = 0

    config = LedgerMasterConfig.objects.create(is_active=True)

    if fallback_gl.exists():
        try:
            df_gl = pd.read_excel(fallback_gl)
            gl_count = len(df_gl)
            with open(fallback_gl, "rb") as f:
                config.gl_file.save("gl_account_list.xlsx", f, save=False)
        except Exception as e:
            logger.warning("Could not seed GL master file: {}", e)

    if fallback_sloc.exists():
        try:
            df_sloc = pd.read_excel(fallback_sloc)
            sloc_count = len(df_sloc)
            with open(fallback_sloc, "rb") as f:
                config.sloc_file.save("sloc_desc.xlsx", f, save=False)
        except Exception as e:
            logger.warning("Could not seed SLoc master file: {}", e)

    config.gl_account_count = gl_count
    config.sloc_count = sloc_count
    config.save()
    logger.info("Initialized background master config: {} GLs, {} SLocs", gl_count, sloc_count)
    return config


def _get_or_load_backend_dataset() -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """
    Retrieves cached backend dataset or seeds the initial 2 Excel files
    (sample_prpo_extract.xlsx and sample_mara_master.xlsx) from the backend.
    """
    df_cache = PERSISTENT_CACHE_DIR / "df.json"
    df2_cache = PERSISTENT_CACHE_DIR / "df2.json"

    if df_cache.exists() and df2_cache.exists():
        try:
            df = pd.read_json(df_cache, orient="split")
            df2 = pd.read_json(df2_cache, orient="split")
            return df, df2
        except Exception as e:
            logger.warning("Could not read cached backend dataset: {}", e)

    prpo_sample = BACKEND_DATA_DIR / "sample_prpo_extract.xlsx"
    mara_sample = BACKEND_DATA_DIR / "sample_mara_master.xlsx"

    if prpo_sample.exists():
        logger.info("Initializing Q-Ledger with backend seed Excel files: {}", prpo_sample)
        with open(prpo_sample, "rb") as f_prpo:
            prpo_content = f_prpo.read()
            df = process_data([ContentFile(prpo_content, name="sample_prpo_extract.xlsx")])

        df2 = None
        if mara_sample.exists():
            with open(mara_sample, "rb") as f_mara:
                mara_content = f_mara.read()
                df2 = process_mara_data([ContentFile(mara_content, name="sample_mara_master.xlsx")])

        if df is not None and not df.empty:
            if df2 is None or df2.empty:
                df2 = df[["Material"]].copy()
                df2["Material Type"] = "Not Applicable"
                df2 = df2.drop_duplicates(subset=["Material"])

            df, df2 = dfmain(df, df2)

            df.to_json(df_cache, orient="split", date_format="iso")
            df2.to_json(df2_cache, orient="split", date_format="iso")

            if not LedgerDataset.objects.filter(is_active=True).exists():
                dataset = LedgerDataset.objects.create(
                    title="Seed SAP ERP Audit Dataset (Hyundai Ecosystem)",
                    record_count=len(df),
                    total_spend=float(df["Amount LC"].sum()) if "Amount LC" in df.columns else 0.0,
                    is_active=True,
                )
                with open(prpo_sample, "rb") as pf:
                    dataset.prpo_file.save("sample_prpo_extract.xlsx", pf, save=False)
                if mara_sample.exists():
                    with open(mara_sample, "rb") as mf:
                        dataset.mara_file.save("sample_mara_master.xlsx", mf, save=False)
                dataset.save()

            return df, df2

    return None, None


@csrf_protect
def dashboard_view(request):
    """
    Main Q-Ledger Forensic Investigation Dashboard.
    Provides standard ForensiQ page header, KPI cards, visual charts, and 7 forensic checkpoints.
    """
    master_config = _ensure_masters_initialized()

    context: dict = {
        "vendor_list": [],
        "selected_vendor": "",
        "record_count": 0,
        "master_config": master_config,
        "gl_account_count": master_config.gl_account_count,
        "sloc_count": master_config.sloc_count,
    }

    try:
        if request.method == "POST":
            action = request.POST.get("action", "")

            # ----------------------------------------------------
            # 1. FIRST-TIME GL & SLOC MASTER EXCEL UPLOAD
            # ----------------------------------------------------
            if (
                action == "upload_masters"
                or "gl_file" in request.FILES
                or "sloc_file" in request.FILES
            ):
                gl_file = request.FILES.get("gl_file")
                sloc_file = request.FILES.get("sloc_file")

                gl_count = master_config.gl_account_count
                sloc_count = master_config.sloc_count

                if gl_file:
                    try:
                        df_gl = pd.read_excel(gl_file)
                        gl_count = len(df_gl)
                        master_config.gl_file.save(gl_file.name, gl_file, save=False)
                        logger.info("Uploaded new G/L Master with {} accounts", gl_count)
                    except Exception as e:
                        logger.error("Failed to parse uploaded GL Master: {}", e)

                if sloc_file:
                    try:
                        df_sloc = pd.read_excel(sloc_file)
                        sloc_count = len(df_sloc)
                        master_config.sloc_file.save(sloc_file.name, sloc_file, save=False)
                        logger.info("Uploaded new SLoc Master with {} locations", sloc_count)
                    except Exception as e:
                        logger.error("Failed to parse uploaded SLoc Master: {}", e)

                master_config.gl_account_count = gl_count
                master_config.sloc_count = sloc_count
                master_config.save()

                # Clear cache so data is re-enriched with new master files
                for cache_file in PERSISTENT_CACHE_DIR.glob("*.json"):
                    try:
                        cache_file.unlink()
                    except Exception as e:
                        logger.debug("Cache file delete error: {}", e)

                context["message_success"] = (
                    f"Successfully stored GL Account ({gl_count:,}) and SLoc ({sloc_count:,}) "
                    "master files in the background."
                )

            # ----------------------------------------------------
            # 2. PR/PO & MARA TRANSACTIONAL EVIDENCE UPLOAD
            # ----------------------------------------------------
            elif (
                action == "upload" or "prpo_file" in request.FILES or "prpo_files" in request.FILES
            ):
                prpo_files = request.FILES.getlist("prpo_file") or request.FILES.getlist(
                    "prpo_files"
                )
                mara_files = request.FILES.getlist("mara_file") or request.FILES.getlist(
                    "mara_files"
                )

                if prpo_files:
                    logger.info(
                        "Ingesting {} PR/PO files and {} MARA master files",
                        len(prpo_files),
                        len(mara_files),
                    )
                    df = process_data(prpo_files)
                    df2 = process_mara_data(mara_files)

                    if df is not None and not df.empty:
                        if df2 is None or df2.empty:
                            df2 = df[["Material"]].copy()
                            df2["Material Type"] = "Not Applicable"
                            df2 = df2.drop_duplicates(subset=["Material"])

                        df, df2 = dfmain(df, df2)

                        # Save permanently to media backend storage
                        df_cache = PERSISTENT_CACHE_DIR / "df.json"
                        df2_cache = PERSISTENT_CACHE_DIR / "df2.json"
                        df.to_json(df_cache, orient="split", date_format="iso")
                        df2.to_json(df2_cache, orient="split", date_format="iso")

                        # Create backend dataset record
                        first_prpo = prpo_files[0]
                        first_mara = mara_files[0] if mara_files else None

                        dataset = LedgerDataset.objects.create(
                            title=getattr(first_prpo, "name", "SAP PR/PO Upload"),
                            record_count=len(df),
                            total_spend=float(df["Amount LC"].sum())
                            if "Amount LC" in df.columns
                            else 0.0,
                            is_active=True,
                        )
                        dataset.prpo_file.save(first_prpo.name, first_prpo, save=False)
                        if first_mara:
                            dataset.mara_file.save(first_mara.name, first_mara, save=False)
                        dataset.save()

                        request.session["selected_vendor"] = ""
                        context["message_success"] = (
                            f"Successfully ingested and stored {len(df):,} SAP records in the backend."
                        )
                    else:
                        context["message_error"] = (
                            "Failed to parse PR/PO records. Please verify file structure."
                        )

            # ----------------------------------------------------
            # 3. VENDOR FILTER DRILLDOWN
            # ----------------------------------------------------
            elif "vendor_filter" in request.POST:
                selected_vendor = request.POST.get("vendor_filter", "").strip()
                request.session["selected_vendor"] = selected_vendor

        # ----------------------------------------------------
        # 4. RETRIEVE ACTIVE BACKEND DATASET
        # ----------------------------------------------------
        df, df2 = _get_or_load_backend_dataset()

        if df is not None and not df.empty:
            vendor_list = sorted(
                [
                    str(v)
                    for v in df["Vendor Code & Name"].dropna().unique().tolist()
                    if str(v).strip()
                ]
            )
            context["vendor_list"] = vendor_list

            selected_vendor = request.session.get("selected_vendor", "")
            context["selected_vendor"] = selected_vendor
            context["is_vendor_filtered"] = bool(selected_vendor)

            filtered_df = df.copy()
            if selected_vendor:
                filtered_df = filtered_df[filtered_df["Vendor Code & Name"] == selected_vendor]

            context["record_count"] = len(filtered_df)

            filtered_df.to_json(
                PERSISTENT_CACHE_DIR / "filtered_df.json", orient="split", date_format="iso"
            )

            # ----------------------------------------------------
            # 5. FORENSIC KPIS
            # ----------------------------------------------------
            total_spend_raw = (
                filtered_df["Amount LC"].sum() if "Amount LC" in filtered_df.columns else 0
            )
            context["total_amount"] = indian_rupee_format(total_spend_raw)
            context["total_amount_raw"] = int(total_spend_raw)

            context["vendor_count"] = (
                filtered_df["Vendor"].nunique() if "Vendor" in filtered_df.columns else 0
            )
            context["material_count"] = (
                filtered_df["Material"].nunique() if "Material" in filtered_df.columns else 0
            )
            context["cost_count"] = (
                filtered_df["Cost Ctr"].nunique() if "Cost Ctr" in filtered_df.columns else 0
            )
            context["gl_count"] = (
                filtered_df["G/L acct"].nunique() if "G/L acct" in filtered_df.columns else 0
            )
            context["po_count"] = (
                filtered_df["Purchase order"].nunique()
                if "Purchase order" in filtered_df.columns
                else 0
            )
            context["creator_count"] = (
                filtered_df["Creater"].nunique() if "Creater" in filtered_df.columns else 0
            )

            # ----------------------------------------------------
            # 6. TOP SUMMARY RANKINGS
            # ----------------------------------------------------
            if (
                not selected_vendor
                and "Vendor" in filtered_df.columns
                and "Name 1" in filtered_df.columns
            ):
                top_vendor_df = (
                    filtered_df.groupby(["Vendor", "Name 1"])["Amount LC"]
                    .sum()
                    .reset_index()
                    .sort_values(by="Amount LC", ascending=False)
                    .head(5)
                )
                top_vendor_df["Formatted_Amount"] = top_vendor_df["Amount LC"].apply(
                    indian_rupee_format
                )
                top_vendor_df = top_vendor_df.rename(
                    columns={"Vendor": "vendor_id", "Name 1": "vendor_name"}
                )
                context["top_vendors"] = top_vendor_df.to_dict(orient="records")
            else:
                context["top_vendors"] = []

            if "G/L acct" in filtered_df.columns:
                top_gl_df = (
                    filtered_df.groupby("G/L acct")["Amount LC"]
                    .sum()
                    .reset_index()
                    .sort_values(by="Amount LC", ascending=False)
                    .head(5)
                )
                top_gl_df["Formatted_Amount"] = top_gl_df["Amount LC"].apply(indian_rupee_format)
                top_gl_df = top_gl_df.rename(columns={"G/L acct": "gl_account"})
                context["top_gl"] = top_gl_df.to_dict(orient="records")

            if "S/Loc" in filtered_df.columns:
                top_sloc_df = (
                    filtered_df.groupby("S/Loc")["Amount LC"]
                    .sum()
                    .reset_index()
                    .sort_values(by="Amount LC", ascending=False)
                    .head(5)
                )
                top_sloc_df["Formatted_Amount"] = top_sloc_df["Amount LC"].apply(
                    indian_rupee_format
                )
                top_sloc_df = top_sloc_df.rename(columns={"S/Loc": "sloc_code"})
                context["top_sloc"] = top_sloc_df.to_dict(orient="records")

            # ----------------------------------------------------
            # 7. PLOTLY CHARTS
            # ----------------------------------------------------
            try:
                top_gl_pivot = (
                    filtered_df.groupby(["G/L acct", "Cost Ctr"])["Amount LC"].sum().reset_index()
                )
                vendor_fig = row2_c1(top_gl_pivot, filtered_df)
                context["vendor_chart_html"] = vendor_fig.to_html(
                    full_html=False, include_plotlyjs="cdn", config={"displayModeBar": False}
                )
            except Exception as e:
                logger.debug("Vendor chart generation error: {}", e)
                context["vendor_chart_html"] = None

            try:
                cost_fig = row2_c2(filtered_df)
                context["cost_chart_html"] = cost_fig.to_html(
                    full_html=False, include_plotlyjs=False, config={"displayModeBar": False}
                )
            except Exception as e:
                logger.debug("Cost chart generation error: {}", e)
                context["cost_chart_html"] = None

            try:
                _, gl_fig = row2_c3(filtered_df)
                context["gl_chart_html"] = gl_fig.to_html(
                    full_html=False, include_plotlyjs=False, config={"displayModeBar": False}
                )
            except Exception as e:
                logger.debug("GL chart generation error: {}", e)
                context["gl_chart_html"] = None

            # ----------------------------------------------------
            # 8. FORENSIC ANOMALY CHECKPOINTS
            # ----------------------------------------------------
            try:
                mat_df = mater_list(filtered_df.copy(), filtered_df.copy())
                context["checkpoint_material"] = prepare_table_dict(mat_df)
            except Exception as e:
                logger.debug("Material table error: {}", e)
                context["checkpoint_material"] = {"error": str(e)}

            try:
                ersa_df = ersa(
                    filtered_df.copy(), df2.copy() if df2 is not None else filtered_df.copy()
                )
                context["checkpoint_ersa"] = prepare_table_dict(ersa_df)
            except Exception as e:
                logger.debug("ERSA table error: {}", e)
                context["checkpoint_ersa"] = {"error": str(e)}

            try:
                openpo_df = openpo(filtered_df.copy())
                context["checkpoint_openpo"] = prepare_table_dict(openpo_df)
            except Exception as e:
                logger.debug("Open PO table error: {}", e)
                context["checkpoint_openpo"] = {"error": str(e)}

            try:
                unitprice_df = indir_mat(filtered_df.copy())
                context["checkpoint_unitprice"] = prepare_table_dict(unitprice_df)
            except Exception as e:
                logger.debug("Unit price table error: {}", e)
                context["checkpoint_unitprice"] = {"error": str(e)}

            try:
                _, _, diffmat_df = dif_mat3(
                    filtered_df.copy(), df2.copy() if df2 is not None else filtered_df.copy()
                )
                context["checkpoint_diffmaterial"] = prepare_table_dict(diffmat_df)
            except Exception as e:
                logger.debug("Diff material table error: {}", e)
                context["checkpoint_diffmaterial"] = {"error": str(e)}

            try:
                receiptgap_df, _ = tab66(filtered_df.copy())
                context["checkpoint_receiptgap"] = prepare_table_dict(receiptgap_df)
            except Exception as e:
                logger.debug("Receipt gap table error: {}", e)
                context["checkpoint_receiptgap"] = {"error": str(e)}

            try:
                receipt1year_df, err = process_data_t7(filtered_df.copy())
                if err:
                    context["checkpoint_receipt1year"] = {"error": err}
                else:
                    context["checkpoint_receipt1year"] = prepare_table_dict(receipt1year_df)
            except Exception as e:
                logger.debug("Receipt 1 year table error: {}", e)
                context["checkpoint_receipt1year"] = {"error": str(e)}

    except Exception as ex:
        logger.error("Error in Q-Ledger dashboard: {}", ex)
        context["message_error"] = str(ex)

    return render(request, "q_ledger/dashboard.html", context)


def export_current_view(request):
    """
    Exports the current filtered dataset as an Excel spreadsheet (.xlsx).
    """
    file_path = PERSISTENT_CACHE_DIR / "filtered_df.json"

    if not file_path.exists():
        file_path = PERSISTENT_CACHE_DIR / "df.json"
        if not file_path.exists():
            return HttpResponse("No filtered data available for export.", status=404)

    df = pd.read_json(file_path, orient="split")

    selected_vendor = request.session.get("selected_vendor", "")
    if selected_vendor:
        safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in selected_vendor)
        filename = f"QLedger_{safe_name}.xlsx"
    else:
        filename = "QLedger_Consolidated_Vendors.xlsx"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    df.to_excel(response, index=False, engine="openpyxl")
    return response


def reset_data_view(request):
    """
    Resets the active dataset cache back to default seed state.
    """
    request.session["selected_vendor"] = ""
    for cache_file in PERSISTENT_CACHE_DIR.glob("*.json"):
        try:
            cache_file.unlink()
        except Exception as e:
            logger.debug("Could not remove cache file {}: {}", cache_file, e)
    return redirect("/ledger/")
