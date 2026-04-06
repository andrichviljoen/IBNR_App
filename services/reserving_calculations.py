from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class ReservingResult:
    cumulative_triangle: pd.DataFrame
    link_ratio_matrix: pd.DataFrame
    selected_link_ratios: pd.Series
    cdfs: pd.Series
    latest_diagonal: pd.Series
    ultimate: pd.Series
    ibnr: pd.Series
    summary: pd.DataFrame



def ensure_cumulative(wide_df: pd.DataFrame, triangle_type: str) -> pd.DataFrame:
    """Convert incremental triangle to cumulative when needed."""
    if triangle_type.lower() == "cumulative":
        return wide_df.copy()
    return wide_df.cumsum(axis=1)



def calculate_link_ratios(cumulative_triangle: pd.DataFrame) -> pd.DataFrame:
    """Calculate age-to-age link ratios for each development period pair."""
    cols = list(cumulative_triangle.columns)
    ratio_df = pd.DataFrame(index=cumulative_triangle.index)
    for i in range(len(cols) - 1):
        curr_col = cols[i]
        next_col = cols[i + 1]
        numer = cumulative_triangle[next_col]
        denom = cumulative_triangle[curr_col]
        ratio_df[f"{curr_col}->{next_col}"] = np.where((denom > 0) & numer.notna(), numer / denom, np.nan)
    return ratio_df



def volume_weighted_factors(cumulative_triangle: pd.DataFrame) -> pd.Series:
    """Compute volume-weighted average link ratios by development pair."""
    cols = list(cumulative_triangle.columns)
    factors: Dict[str, float] = {}
    for i in range(len(cols) - 1):
        c = cols[i]
        n = cols[i + 1]
        valid = cumulative_triangle[[c, n]].dropna()
        valid = valid[valid[c] > 0]
        if valid.empty:
            factors[f"{c}->{n}"] = np.nan
        else:
            factors[f"{c}->{n}"] = valid[n].sum() / valid[c].sum()
    return pd.Series(factors)



def cdf_from_link_ratios(selected_link_ratios: pd.Series) -> pd.Series:
    """Build cumulative development factors to ultimate."""
    ldfs = selected_link_ratios.fillna(1.0).values
    cdfs: List[float] = []
    for i in range(len(ldfs)):
        cdfs.append(float(np.prod(ldfs[i:])))
    return pd.Series(cdfs, index=selected_link_ratios.index)



def latest_diagonal(cumulative_triangle: pd.DataFrame) -> pd.Series:
    """Extract latest observed cumulative amount by origin period."""
    vals = {}
    for idx, row in cumulative_triangle.iterrows():
        observed = row.dropna()
        vals[idx] = observed.iloc[-1] if not observed.empty else np.nan
    return pd.Series(vals)



def run_chain_ladder(
    wide_df: pd.DataFrame,
    triangle_type: str,
    excluded_pairs: List[str] | None = None,
) -> ReservingResult:
    """Run a simple deterministic chain-ladder workflow."""
    excluded_pairs = excluded_pairs or []
    cumulative = ensure_cumulative(wide_df, triangle_type)
    ratios = calculate_link_ratios(cumulative)
    selected = volume_weighted_factors(cumulative)
    for pair in excluded_pairs:
        if pair in selected.index:
            selected[pair] = 1.0
    cdfs = cdf_from_link_ratios(selected)

    cols = list(cumulative.columns)
    latest = latest_diagonal(cumulative)
    latest_step = cumulative.apply(lambda row: row.dropna().index[-1] if row.dropna().size else np.nan, axis=1)

    pair_to_step = {f"{cols[i]}->{cols[i + 1]}": cols[i] for i in range(len(cols) - 1)}
    step_to_cdf = {pair_to_step[idx]: cdf for idx, cdf in cdfs.items()}

    ultimate = pd.Series(index=cumulative.index, dtype=float)
    for origin in cumulative.index:
        step = latest_step.loc[origin]
        multiplier = step_to_cdf.get(step, 1.0)
        ultimate.loc[origin] = latest.loc[origin] * multiplier

    ibnr = ultimate - latest
    summary = pd.DataFrame(
        {
            "latest": latest,
            "ultimate": ultimate,
            "ibnr": ibnr,
        }
    )

    total = pd.DataFrame({"latest": [latest.sum()], "ultimate": [ultimate.sum()], "ibnr": [ibnr.sum()]}, index=["Total"])
    summary = pd.concat([summary, total])

    return ReservingResult(
        cumulative_triangle=cumulative,
        link_ratio_matrix=ratios,
        selected_link_ratios=selected,
        cdfs=cdfs,
        latest_diagonal=latest,
        ultimate=ultimate,
        ibnr=ibnr,
        summary=summary,
    )
