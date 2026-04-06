from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass
class ValidationResult:
    errors: List[str]
    warnings: List[str]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0



def validate_triangle_shape(rows: List[List[str]]) -> ValidationResult:
    """Validate basic row/column shape for pasted grid."""
    errors: List[str] = []
    warnings: List[str] = []

    if not rows:
        errors.append("Triangle input is empty.")
        return ValidationResult(errors, warnings)

    if len(rows) < 2:
        errors.append("Triangle requires a header row and at least one data row.")
        return ValidationResult(errors, warnings)

    expected_len = len(rows[0])
    if expected_len < 2:
        errors.append("Header row must include an origin column and at least one development column.")

    for idx, row in enumerate(rows, start=1):
        if len(row) != expected_len:
            errors.append(
                f"Jagged row detected at row {idx}: expected {expected_len} columns but found {len(row)}."
            )

    return ValidationResult(errors, warnings)



def validate_origins(origins: List[str], expected_origins: List[str]) -> ValidationResult:
    """Validate origin labels against expected sequence."""
    errors: List[str] = []
    warnings: List[str] = []

    if len(set(origins)) != len(origins):
        seen = set()
        dups = []
        for origin in origins:
            if origin in seen:
                dups.append(origin)
            seen.add(origin)
        errors.append(f"Duplicate origin periods found: {sorted(set(dups))}")

    missing = [o for o in expected_origins if o not in origins]
    extra = [o for o in origins if o not in expected_origins]

    if missing:
        warnings.append(f"Configured origin periods missing from pasted triangle: {missing}")
    if extra:
        errors.append(f"Origin periods outside configured range: {extra}")

    return ValidationResult(errors, warnings)



def validate_numeric_cells(df: pd.DataFrame) -> ValidationResult:
    """Validate numeric body values are finite if present."""
    errors: List[str] = []
    warnings: List[str] = []

    if df.empty:
        errors.append("Triangle body is empty.")
        return ValidationResult(errors, warnings)

    for row_idx in df.index:
        for col in df.columns:
            value = df.at[row_idx, col]
            if pd.isna(value):
                continue
            if not isinstance(value, (int, float)):
                errors.append(f"Invalid numeric value at origin '{row_idx}', development '{col}': {value}")

    return ValidationResult(errors, warnings)
