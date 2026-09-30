"""
Q-Ledger Data Preprocessing Service
Handles parsing and merging of SAP PR/PO, MARA, GL Account, and SLoc datasets.
"""

from pathlib import Path

import pandas as pd
from django.conf import settings
from loguru import logger

from .analysis_functions import material_type_data

BASE_DIR = Path(__file__).resolve().parent.parent
MASTERS_DIR = Path(settings.MEDIA_ROOT) / "q_ledger" / "masters"
MASTERS_DIR.mkdir(parents=True, exist_ok=True)


def get_master_gl_data() -> pd.DataFrame:
    """
    Retrieves the G/L Account master dataset stored in the background.
    Checks database config, media storage, and initial assets directory.
    """
    from q_ledger.models import LedgerMasterConfig

    config = LedgerMasterConfig.objects.filter(is_active=True).first()
    if config and config.gl_file:
        try:
            return pd.read_excel(config.gl_file.path)
        except Exception as e:
            logger.warning("Could not read GL master file from model: {}", e)

    stored_gl = MASTERS_DIR / "gl_account_list.xlsx"
    if stored_gl.exists():
        return pd.read_excel(stored_gl)

    fallback_gl = BASE_DIR / "assets" / "GL Acct Data" / "GL account list.xlsx"
    if fallback_gl.exists():
        return pd.read_excel(fallback_gl)

    return pd.DataFrame(columns=["G/L acct", "G/L Acct Long Text"])


def get_master_sloc_data() -> pd.DataFrame:
    """
    Retrieves the Storage Location (SLoc) master dataset stored in the background.
    """
    from q_ledger.models import LedgerMasterConfig

    config = LedgerMasterConfig.objects.filter(is_active=True).first()
    if config and config.sloc_file:
        try:
            return pd.read_excel(config.sloc_file.path)
        except Exception as e:
            logger.warning("Could not read SLoc master file from model: {}", e)

    stored_sloc = MASTERS_DIR / "sloc_desc.xlsx"
    if stored_sloc.exists():
        return pd.read_excel(stored_sloc)

    fallback_sloc = BASE_DIR / "assets" / "SLoc Desc" / "Sloc Desc.xlsx"
    if fallback_sloc.exists():
        return pd.read_excel(fallback_sloc)

    return pd.DataFrame(columns=["Plnt", "S/Loc", "S/loc Description"])


def dfmain(main_df: pd.DataFrame, df2: pd.DataFrame):
    """
    Enriches PR/PO dataframe with MARA, G/L master, and SLoc master data stored in background.
    """
    logger.info("Enriching Q-Ledger PR/PO dataframe with background GL and SLoc masters")
    main_df = main_df.copy()
    main_df["year"] = pd.to_datetime(main_df["PO Date"], errors="coerce").dt.year
    main_df = pd.merge(main_df, df2[["Material", "Material Type"]], on="Material", how="left")

    # 1. Merge G/L Account Master Data from background store
    gl_data = get_master_gl_data()
    if not gl_data.empty:
        main_df = pd.merge(main_df, gl_data, left_on="G/L acct", right_on="G/L acct", how="left")
    else:
        main_df["G/L Acct Long Text_x"] = "N/A"

    # 2. Merge SLoc Master Data from background store
    sloc_data = get_master_sloc_data()
    if not sloc_data.empty and "S/Loc" in sloc_data.columns:
        cols = [c for c in ["S/Loc", "S/loc Description"] if c in sloc_data.columns]
        main_df = pd.merge(main_df, sloc_data[cols], on="S/Loc", how="left")
        if "S/loc Description" in main_df.columns:
            main_df["S/Loc Description"] = main_df["S/loc Description"].fillna("N/A")
            main_df["S/Loc."] = (
                main_df["S/Loc"].astype(str) + " - " + main_df["S/Loc Description"].astype(str)
            )
    else:
        main_df["S/Loc."] = main_df["S/Loc"].astype(str)

    material_type_mapping = dict(
        zip(
            material_type_data["Material Type"],
            material_type_data["Material Type Description"],
            strict=False,
        )
    )

    main_df["Material Type Description"] = main_df["Material Type"].map(material_type_mapping)
    main_df["Vendor Code & Name"] = (
        main_df["Vendor"].astype(str) + " - " + main_df["Name 1"].astype(str)
    )
    main_df["Cost Ctr"] = main_df["Cost Ctr"].fillna("none")
    main_df["Material Type"] = main_df["Material Type"].fillna("Not Applicable")
    main_df["Material Type Description"] = main_df["Material Type"].map(material_type_mapping)
    main_df["Amount LC"] = main_df["Amount LC"].fillna(0).astype(int)

    main_df["Material Type."] = (
        main_df["Material Type"].astype(str)
        + " - "
        + main_df["Material Type Description"].astype(str)
    )

    gl_text_col = (
        "G/L Acct Long Text_x"
        if "G/L Acct Long Text_x" in main_df.columns
        else ("G/L Acct Long Text" if "G/L Acct Long Text" in main_df.columns else None)
    )
    if gl_text_col:
        main_df["G/L acct."] = (
            main_df["G/L acct"].astype(str) + " - " + main_df[gl_text_col].astype(str)
        )
    else:
        main_df["G/L acct."] = main_df["G/L acct"].astype(str)

    cost_name_col = (
        "Cost Center name"
        if "Cost Center name" in main_df.columns
        else ("Cost Center Name" if "Cost Center Name" in main_df.columns else None)
    )
    if cost_name_col:
        main_df["Cost Ctr."] = (
            main_df["Cost Ctr"].astype(str) + " - " + main_df[cost_name_col].astype(str)
        )
    else:
        main_df["Cost Ctr."] = main_df["Cost Ctr"].astype(str)

    return main_df, df2


def process_data(all_files) -> pd.DataFrame | None:
    """
    Processes multiple PR/PO Excel files and merges with background G/L and SLoc masters.
    """
    if not all_files:
        return None

    logger.info("Processing {} PR/PO evidence files", len(all_files))
    dfs = []
    for file in all_files:
        try:
            main_df = pd.read_excel(file)
            dfs.append(main_df)
        except Exception as e:
            logger.error("Failed to read Excel file {}: {}", getattr(file, "name", str(file)), e)

    if not dfs:
        return None

    main_df = pd.concat(dfs, ignore_index=True)

    if "Supplier" in main_df.columns and "Vendor" not in main_df.columns:
        main_df.rename(columns={"Supplier": "Vendor"}, inplace=True)

    if "G/L Acct" in main_df.columns and "G/L acct" not in main_df.columns:
        main_df.rename(columns={"G/L Acct": "G/L acct"}, inplace=True)

    if "G/L acct" in main_df.columns:
        main_df["G/L acct"] = main_df["G/L acct"].fillna("0000")
    else:
        main_df["G/L acct"] = pd.Series(["0000"] * len(main_df))

    if "PO Currency" in main_df.columns:
        main_df["PO Currency"] = main_df["PO Currency"].fillna("<NA>")
    else:
        main_df["PO Currency"] = pd.Series(["<NA>"] * len(main_df))

    # Join GL master data from background store
    gl_data = get_master_gl_data()
    if not gl_data.empty:
        main_df = pd.merge(main_df, gl_data, left_on="G/L acct", right_on="G/L acct", how="left")

    main_df = main_df.drop_duplicates()
    main_df["Pstng Date"] = pd.to_datetime(main_df["Pstng Date"], errors="coerce")
    main_df["PO Date"] = pd.to_datetime(main_df["PO Date"], errors="coerce")
    main_df["Amount LC"] = main_df["Amount LC"].fillna(0.0)
    main_df["G/L acct"] = (
        pd.to_numeric(main_df["G/L acct"], errors="coerce").fillna(0).astype("int64")
    )
    main_df = main_df.dropna(subset=["Pstng Date"])

    if "Storage Location" in main_df.columns:
        main_df = main_df.rename(columns={"Storage Location": "S/Loc"})
    elif "S/Loc" not in main_df.columns:
        main_df["S/Loc"] = "N/A"

    if "PO Rem" not in main_df.columns:
        if "PO Qty" in main_df.columns and "GR Qty" in main_df.columns:
            main_df["PO Rem"] = main_df["PO Qty"] - main_df["GR Qty"]
        else:
            main_df["PO Rem"] = 0

    required_columns = [
        "S/Loc",
        "Vendor",
        "Name 1",
        "Creater",
        "Material",
        "Description",
        "Spec",
        "PO Rem",
        "Unit",
        "G/L acct",
        "G/L Acct Long Text" if "G/L Acct Long Text" in main_df.columns else "G/L acct",
        "Cost Ctr",
        "Cost Center name" if "Cost Center name" in main_df.columns else "Cost Ctr",
        "PO Date",
        "Purchase order",
        "PO Currency",
        "Net price",
        "PO Qty",
        "Pstng Date",
        "GR Qty",
        "Amount LC",
    ]

    for col in required_columns:
        if col not in main_df.columns:
            main_df[col] = "N/A"

    main_df = main_df[required_columns]
    logger.info("Successfully processed {} PR/PO records", len(main_df))
    return main_df


def process_mara_data(all_files) -> pd.DataFrame | None:
    """
    Processes MARA material master Excel files and extracts Material & Material Type.
    """
    if not all_files:
        return None

    logger.info("Processing {} MARA master files", len(all_files))
    dfs = []
    for file in all_files:
        try:
            mara_df = pd.read_excel(file, header=3)
            if "Material" in mara_df.columns and "Material Type" in mara_df.columns:
                mara_df = mara_df[["Material", "Material Type"]]
                dfs.append(mara_df)
            else:
                mara_df_alt = pd.read_excel(file)
                if "Material" in mara_df_alt.columns and "Material Type" in mara_df_alt.columns:
                    dfs.append(mara_df_alt[["Material", "Material Type"]])
        except Exception as e:
            logger.error("Failed to parse MARA file {}: {}", getattr(file, "name", str(file)), e)

    if not dfs:
        return None

    return pd.concat(dfs, ignore_index=True).drop_duplicates()
