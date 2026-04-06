from __future__ import annotations

from datetime import date, datetime
import re
from typing import List

import pandas as pd


GRAIN_TO_MONTHS = {
    "Monthly": 1,
    "Quarterly": 3,
    "Semi-Annual": 6,
    "Annual": 12,
}



def parse_config_period(value: str, grain: str) -> pd.Period:
    """Parse configured period text into a pandas Period aligned to selected grain."""
    cleaned = value.strip()
    if grain == "Monthly":
        return pd.Period(cleaned, freq="M")
    if grain == "Quarterly":
        normalized = cleaned.upper().replace("-", "").replace(" ", "")
        if re.match(r"^\d{4}Q[1-4]$", normalized):
            return pd.Period(normalized, freq="Q")
        return pd.Period(pd.to_datetime(cleaned), freq="Q")
    if grain == "Semi-Annual":
        return _parse_semi_annual(cleaned)
    if grain == "Annual":
        if re.match(r"^\d{4}$", cleaned):
            return pd.Period(cleaned, freq="Y")
        return pd.Period(pd.to_datetime(cleaned), freq="Y")
    raise ValueError(f"Unsupported grain: {grain}")



def canonical_origin_label(period: pd.Period, grain: str) -> str:
    """Create canonical display label for origin period."""
    if grain == "Monthly":
        return period.to_timestamp().strftime("%b %Y")
    if grain == "Quarterly":
        return f"{period.year}Q{period.quarter}"
    if grain == "Semi-Annual":
        half = 1 if period.start_time.month <= 6 else 2
        return f"{period.year}H{half}"
    if grain == "Annual":
        return str(period.year)
    raise ValueError(f"Unsupported grain: {grain}")



def generate_origin_sequence(start: str, end: str, grain: str) -> List[str]:
    """Generate canonical origin labels between configured start and end values."""
    start_period = parse_config_period(start, grain)
    end_period = parse_config_period(end, grain)
    if start_period > end_period:
        raise ValueError("Origin start period must be before or equal to origin end period.")

    if grain == "Semi-Annual":
        step_months = 6
        seq = []
        current = start_period
        while current <= end_period:
            seq.append(canonical_origin_label(current, grain))
            current = pd.Period(current.start_time + pd.DateOffset(months=step_months), freq="6M")
        return seq

    freq = {
        "Monthly": "M",
        "Quarterly": "Q",
        "Annual": "Y",
    }[grain]
    periods = pd.period_range(start_period, end_period, freq=freq)
    return [canonical_origin_label(p, grain) for p in periods]



def normalize_origin_label(raw_label: str, grain: str) -> str:
    """Normalize user-pasted origin label into canonical label for the selected grain."""
    raw = str(raw_label).strip()
    if not raw:
        raise ValueError("Blank origin label")

    if grain == "Annual":
        match = re.match(r"^(\d{4})$", raw)
        if match:
            return match.group(1)
        dt = pd.to_datetime(raw)
        return str(dt.year)

    if grain == "Quarterly":
        upper = raw.upper().replace(" ", "").replace("-", "")
        q_match = re.match(r"^(\d{4})Q([1-4])$", upper)
        if q_match:
            return f"{q_match.group(1)}Q{q_match.group(2)}"
        dt = pd.to_datetime(raw)
        period = pd.Period(dt, freq="Q")
        return f"{period.year}Q{period.quarter}"

    if grain == "Semi-Annual":
        upper = raw.upper().replace(" ", "").replace("-", "")
        h_match = re.match(r"^(\d{4})H([12])$", upper)
        if h_match:
            return f"{h_match.group(1)}H{h_match.group(2)}"
        dt = pd.to_datetime(raw)
        half = 1 if dt.month <= 6 else 2
        return f"{dt.year}H{half}"

    if grain == "Monthly":
        year_month = re.match(r"^(\d{4})[\-/](\d{1,2})$", raw)
        if year_month:
            dt = date(int(year_month.group(1)), int(year_month.group(2)), 1)
            return dt.strftime("%b %Y")
        dt = pd.to_datetime(raw)
        return pd.Period(dt, freq="M").to_timestamp().strftime("%b %Y")

    raise ValueError(f"Unsupported grain: {grain}")



def _parse_semi_annual(value: str) -> pd.Period:
    cleaned = value.strip().upper().replace(" ", "").replace("-", "")
    match = re.match(r"^(\d{4})H([12])$", cleaned)
    if match:
        year = int(match.group(1))
        month = 1 if match.group(2) == "1" else 7
        return pd.Period(datetime(year, month, 1), freq="6M")

    dt = pd.to_datetime(value)
    month = 1 if dt.month <= 6 else 7
    return pd.Period(datetime(dt.year, month, 1), freq="6M")
