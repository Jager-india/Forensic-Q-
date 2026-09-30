"""
Q-Ledger Forensic Selectors
Read-only queries and data aggregation routines.
"""

from typing import Any

import pandas as pd


def prepare_table_dict(df: pd.DataFrame | None, max_rows: int = 500) -> dict[str, Any]:
    """
    Converts a pandas DataFrame into column headers and JSON-serializable row records
    for high-performance Tabulator.js / HTML table rendering.
    """
    if df is None or df.empty:
        return {"columns": [], "rows": [], "count": 0}

    # Limit rows to prevent browser DOM overload
    limited_df = df.head(max_rows).copy()

    # Fill NaN values cleanly
    limited_df = limited_df.fillna("—")

    columns = [{"title": str(col), "field": str(col)} for col in limited_df.columns]
    records = limited_df.to_dict(orient="records")

    # Ensure all values are strings or numbers
    clean_records = []
    for r in records:
        clean_row = {}
        for k, v in r.items():
            if isinstance(v, pd.Timestamp):
                clean_row[str(k)] = v.strftime("%Y-%m-%d")
            else:
                clean_row[str(k)] = str(v) if not isinstance(v, (int, float, bool)) else v
        clean_records.append(clean_row)

    return {
        "columns": columns,
        "rows": clean_records,
        "count": len(df),
    }
