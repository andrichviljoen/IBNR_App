from __future__ import annotations

from typing import Any

import pandas as pd



def grid_dataframe_to_tsv(df: pd.DataFrame) -> str:
    """Convert an editable grid DataFrame into tab-delimited text for parser consumption.

    The function preserves blank cells and supports both text and numeric values.
    Trailing fully-empty rows/columns are trimmed for cleaner parsing.
    """
    if df is None or df.empty:
        return ""

    work = df.copy()
    work = work.fillna("")

    # Normalize cell values to strings while preserving blanks.
    for col in work.columns:
        work[col] = work[col].apply(_cell_to_string)

    # Trim fully-empty trailing rows.
    while len(work) > 0 and (work.iloc[-1].replace("", pd.NA).isna().all()):
        work = work.iloc[:-1]

    if work.empty:
        return ""

    # Trim fully-empty trailing columns.
    while len(work.columns) > 0 and (work.iloc[:, -1].replace("", pd.NA).isna().all()):
        work = work.iloc[:, :-1]

    if work.empty or len(work.columns) == 0:
        return ""

    lines = ["\t".join(row.tolist()) for _, row in work.iterrows()]
    return "\n".join(lines)



def _cell_to_string(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, str):
        return value
    return str(value)
