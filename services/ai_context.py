from __future__ import annotations

import json
from typing import Any, Dict, List

import pandas as pd

from services.reserving_calculations import ReservingResult
from services.triangle_parser import ParsedTriangle, ParseOptions



def build_ai_context(
    options: ParseOptions,
    parsed: ParsedTriangle,
    reserving: ReservingResult,
    diagnostics_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a structured JSON-serializable context for AI/reporting layer."""
    context = {
        "app_configuration": {
            "origin_start": options.origin_start,
            "origin_end": options.origin_end,
            "grain": options.grain,
            "triangle_type": options.triangle_type,
            "value_type": options.value_type,
            "blank_as_zero": options.blank_as_zero,
            "development_mode": options.development_mode,
        },
        "parsed_origin_periods": parsed.origin_labels,
        "parsed_development_periods": parsed.development_steps,
        "cleaned_triangle": parsed.wide_df.reset_index(names="origin").to_dict(orient="records"),
        "selected_factors": reserving.selected_link_ratios.to_dict(),
        "cdfs": reserving.cdfs.to_dict(),
        "ultimates": reserving.ultimate.to_dict(),
        "ibnr": reserving.ibnr.to_dict(),
        "validation_messages": {
            "errors": parsed.validation.errors,
            "warnings": parsed.validation.warnings,
        },
        "diagnostics_summary": diagnostics_summary,
    }
    return context



def context_to_json(context: Dict[str, Any]) -> str:
    """Serialize context dictionary to pretty JSON string."""
    return json.dumps(context, indent=2, default=_json_default)



def _json_default(obj: Any) -> Any:
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if pd.isna(obj):
        return None
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
