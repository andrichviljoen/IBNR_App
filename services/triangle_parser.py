from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import re

import numpy as np
import pandas as pd

from services.development_periods import normalize_development_headers
from services.origin_periods import generate_origin_sequence, normalize_origin_label
from services.triangle_validation import ValidationResult, validate_numeric_cells, validate_origins, validate_triangle_shape


@dataclass
class ParseOptions:
    grain: str
    origin_start: str
    origin_end: str
    triangle_type: str
    value_type: str
    blank_as_zero: bool = False
    auto_trim: bool = True
    remove_thousand_separators: bool = True
    parentheses_negative: bool = True
    development_mode: str = "steps"  # steps | elapsed_months


@dataclass
class ParsedTriangle:
    wide_df: pd.DataFrame
    long_df: pd.DataFrame
    origin_labels: List[str]
    development_steps: List[int]
    development_labels: List[str]
    validation: ValidationResult



def split_pasted_grid(text: str) -> List[List[str]]:
    """Parse pasted text into rows/columns while preserving blank cells."""
    if not text or not text.strip():
        return []
    lines = [ln.rstrip("\r") for ln in text.split("\n") if ln.strip() != ""]
    rows: List[List[str]] = []
    for line in lines:
        if "\t" in line:
            cols = line.split("\t")
        else:
            cols = re.split(r"\s{2,}|,", line)
        rows.append(cols)
    return rows



def parse_triangle_text(text: str, options: ParseOptions) -> ParsedTriangle:
    """Convert pasted triangle text into validated wide and long formats."""
    rows = split_pasted_grid(text)
    shape_validation = validate_triangle_shape(rows)
    if not shape_validation.is_valid:
        return ParsedTriangle(pd.DataFrame(), pd.DataFrame(), [], [], [], shape_validation)

    header_row = rows[0]
    if len(header_row) < 2:
        shape_validation.errors.append("Missing development header row.")
        return ParsedTriangle(pd.DataFrame(), pd.DataFrame(), [], [], [], shape_validation)

    raw_dev_headers = header_row[1:]
    try:
        development_steps, development_labels = normalize_development_headers(
            raw_dev_headers,
            grain=options.grain,
            header_mode=options.development_mode,
        )
    except ValueError as exc:
        shape_validation.errors.append(str(exc))
        return ParsedTriangle(pd.DataFrame(), pd.DataFrame(), [], [], [], shape_validation)

    expected_origins = generate_origin_sequence(options.origin_start, options.origin_end, options.grain)

    normalized_origins: List[str] = []
    parsed_values: List[List[float]] = []

    for row_idx, row in enumerate(rows[1:], start=2):
        raw_origin = row[0]
        if options.auto_trim:
            raw_origin = raw_origin.strip()
        if raw_origin == "":
            shape_validation.errors.append(f"Missing origin label at row {row_idx}.")
            continue
        try:
            origin = normalize_origin_label(raw_origin, options.grain)
            normalized_origins.append(origin)
        except Exception as exc:  # noqa: BLE001
            shape_validation.errors.append(f"Invalid origin label '{raw_origin}' at row {row_idx}: {exc}")
            continue

        numeric_row: List[float] = []
        for col_idx, raw_value in enumerate(row[1:], start=2):
            value = _clean_numeric_cell(raw_value, options)
            if isinstance(value, str):
                shape_validation.errors.append(
                    f"Invalid numeric value '{raw_value}' at row {row_idx}, column {col_idx}."
                )
                numeric_row.append(np.nan)
            else:
                numeric_row.append(value)
        parsed_values.append(numeric_row)

    if not normalized_origins:
        shape_validation.errors.append("No valid origin periods were parsed.")
        return ParsedTriangle(pd.DataFrame(), pd.DataFrame(), [], [], [], shape_validation)

    origin_validation = validate_origins(normalized_origins, expected_origins)
    shape_validation.errors.extend(origin_validation.errors)
    shape_validation.warnings.extend(origin_validation.warnings)

    wide_df = pd.DataFrame(parsed_values, index=normalized_origins, columns=development_steps, dtype=float)
    numeric_validation = validate_numeric_cells(wide_df)
    shape_validation.errors.extend(numeric_validation.errors)
    shape_validation.warnings.extend(numeric_validation.warnings)

    long_df = wide_df.reset_index(names="origin").melt(
        id_vars="origin", var_name="development", value_name="value"
    )
    origin_order = {origin: idx for idx, origin in enumerate(expected_origins)}
    long_df["origin_index"] = long_df["origin"].map(origin_order).fillna(-1).astype(int)
    long_df["development_index"] = long_df["development"].astype(int)
    long_df["observed_flag"] = ~long_df["value"].isna()
    long_df["triangle_type"] = options.triangle_type
    long_df["value_type"] = options.value_type

    return ParsedTriangle(
        wide_df=wide_df,
        long_df=long_df,
        origin_labels=normalized_origins,
        development_steps=development_steps,
        development_labels=development_labels,
        validation=shape_validation,
    )



def _clean_numeric_cell(raw: str, options: ParseOptions) -> float | str:
    text = str(raw)
    if options.auto_trim:
        text = text.strip()

    if text == "":
        return 0.0 if options.blank_as_zero else np.nan

    if options.parentheses_negative and re.match(r"^\(.*\)$", text):
        text = f"-{text[1:-1]}"

    if options.remove_thousand_separators:
        text = text.replace(",", "")

    try:
        return float(text)
    except ValueError:
        return text
