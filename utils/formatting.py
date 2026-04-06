from __future__ import annotations

import pandas as pd


def format_currency_df(df: pd.DataFrame) -> pd.DataFrame:
    """Format numeric DataFrame values to 2-decimal string display."""
    return df.applymap(lambda x: "" if pd.isna(x) else f"{x:,.2f}")
