from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class DiagnosticsResult:
    missing_map: pd.DataFrame
    maturity_summary: pd.DataFrame
    outlier_flags: pd.DataFrame



def build_diagnostics(cumulative_triangle: pd.DataFrame, link_ratio_matrix: pd.DataFrame) -> DiagnosticsResult:
    """Build diagnostics tables used by UI and reporting."""
    missing_map = cumulative_triangle.isna().astype(int)

    maturity = []
    for origin, row in cumulative_triangle.iterrows():
        observed = row.dropna()
        maturity.append(
            {
                "origin": origin,
                "observed_cells": int(observed.size),
                "latest_dev": observed.index[-1] if observed.size else None,
            }
        )
    maturity_summary = pd.DataFrame(maturity).set_index("origin")

    outlier_flags = pd.DataFrame(index=link_ratio_matrix.index)
    for col in link_ratio_matrix.columns:
        series = link_ratio_matrix[col].dropna()
        if series.empty:
            outlier_flags[col] = False
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_flags[col] = (link_ratio_matrix[col] < lower) | (link_ratio_matrix[col] > upper)

    return DiagnosticsResult(
        missing_map=missing_map,
        maturity_summary=maturity_summary,
        outlier_flags=outlier_flags,
    )
