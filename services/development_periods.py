from __future__ import annotations

from typing import List, Tuple


GRAIN_STEP_MONTHS = {
    "Monthly": 1,
    "Quarterly": 3,
    "Semi-Annual": 6,
    "Annual": 12,
}



def normalize_development_headers(
    headers: List[str],
    grain: str,
    header_mode: str,
) -> Tuple[List[int], List[str]]:
    """Normalize development headers into integer steps and human labels."""
    if not headers:
        raise ValueError("Missing development headers")

    normalized_steps: List[int] = []
    for raw in headers:
        text = str(raw).strip()
        if text == "":
            raise ValueError("Development header contains blank value")
        try:
            value = int(float(text))
        except ValueError as exc:
            raise ValueError(f"Development header '{text}' is not numeric") from exc

        if header_mode == "steps":
            step = value
        else:
            months_per_step = GRAIN_STEP_MONTHS[grain]
            if value % months_per_step != 0:
                raise ValueError(
                    f"Development header {value} is not compatible with {grain} elapsed-month convention"
                )
            step = value // months_per_step

        normalized_steps.append(step)

    if len(set(normalized_steps)) != len(normalized_steps):
        raise ValueError("Duplicate development headers after normalization")

    if sorted(normalized_steps) != normalized_steps:
        raise ValueError("Development headers must be in ascending order")

    labels = [f"Dev {s}" for s in normalized_steps]
    return normalized_steps, labels
