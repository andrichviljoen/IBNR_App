from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

from services.ai_context import build_ai_context, context_to_json
from services.diagnostics import build_diagnostics
from services.grid_input import grid_dataframe_to_tsv
from services.origin_periods import generate_origin_sequence
from services.reserving_calculations import run_chain_ladder
from services.triangle_parser import ParseOptions, parse_triangle_text


st.set_page_config(page_title="Actuarial Triangle App", layout="wide")
st.title("Actuarial Triangle App")
st.caption("Reliable reserving workflow built around user-pasted triangles.")

if "parse_requested" not in st.session_state:
    st.session_state["parse_requested"] = False
if "grid_triangle_text" not in st.session_state:
    st.session_state["grid_triangle_text"] = ""
if "grid_seed" not in st.session_state:
    # Empty Excel-like starter grid users can paste into directly.
    st.session_state["grid_seed"] = pd.DataFrame([["" for _ in range(16)] for _ in range(18)])

with st.sidebar:
    st.header("Configuration")
    grain = st.selectbox("Development Grain", ["Monthly", "Quarterly", "Semi-Annual", "Annual"], index=1)

    default_starts = {
        "Monthly": "2020-01",
        "Quarterly": "2019Q1",
        "Semi-Annual": "2019H1",
        "Annual": "2019",
    }
    default_ends = {
        "Monthly": "2022-12",
        "Quarterly": "2023Q4",
        "Semi-Annual": "2023H2",
        "Annual": "2023",
    }

    origin_start = st.text_input("Origin Start Period", value=default_starts[grain])
    origin_end = st.text_input("Origin End Period", value=default_ends[grain])

    triangle_type = st.radio("Triangle Type", ["Cumulative", "Incremental"], horizontal=True)

    value_type_choice = st.selectbox("Value Type", ["Incurred", "Paid", "Reported", "Custom"])
    value_type = value_type_choice if value_type_choice != "Custom" else st.text_input("Custom Value Type", "Case Outstanding")

    development_mode = st.radio(
        "Development Header Interpretation",
        ["steps", "elapsed_months"],
        format_func=lambda x: "Headers represent steps" if x == "steps" else "Headers represent elapsed months",
    )

    st.subheader("Parsing Options")
    blank_as_zero = st.checkbox("Treat blank cells as zero", value=False)
    auto_trim = st.checkbox("Auto-trim whitespace", value=True)
    remove_thousand_separators = st.checkbox("Remove thousand separators", value=True)
    parentheses_negative = st.checkbox("Interpret (123) as -123", value=True)

st.subheader("Step 1-2: Provide Triangle Input")
input_mode = st.radio("Input mode", ["Paste Text", "Editable Excel-style Grid"], horizontal=True)

if input_mode == "Paste Text":
    example = "\t0\t12\t24\t36\n2019\t100\t150\t180\t190\n2020\t110\t160\t200\t\n2021\t120\t170\t\t\n2022\t130\t\t\t"
    pasted_text = st.text_area(
        "Paste Excel-style triangle (tab-delimited)",
        height=220,
        placeholder=example,
        value=st.session_state.get("grid_triangle_text", ""),
    )
else:
    st.caption("Paste directly from Excel using Ctrl+V. Grid is fully editable.")

    gb = GridOptionsBuilder.from_dataframe(st.session_state["grid_seed"])
    gb.configure_default_column(
        editable=True,
        resizable=True,
        filter=False,
        sortable=False,
        wrapText=False,
    )
    gb.configure_grid_options(
        editable=True,
        enableRangeSelection=True,
        enableClipboard=True,
        rowSelection="multiple",
        suppressRowClickSelection=False,
        domLayout="normal",
    )

    grid_response = AgGrid(
        st.session_state["grid_seed"],
        gridOptions=gb.build(),
        fit_columns_on_grid_load=False,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        allow_unsafe_jscode=False,
        height=420,
        theme="streamlit",
        key="triangle_input_aggrid",
    )

    edited_df = pd.DataFrame(grid_response.get("data", pd.DataFrame()))

    if st.button("Use this grid as triangle input"):
        text_from_grid = grid_dataframe_to_tsv(edited_df)
        st.session_state["grid_triangle_text"] = text_from_grid
        st.session_state["parse_requested"] = True
        st.success("Grid data captured as triangle input.")

    pasted_text = st.session_state.get("grid_triangle_text", "")
    if pasted_text:
        st.caption("Preview of captured grid input")
        st.code(pasted_text)

if st.button("Step 3: Validate and Parse", type="primary"):
    st.session_state["parse_requested"] = True

if st.session_state.get("parse_requested"):
    options = ParseOptions(
        grain=grain,
        origin_start=origin_start,
        origin_end=origin_end,
        triangle_type=triangle_type,
        value_type=value_type,
        blank_as_zero=blank_as_zero,
        auto_trim=auto_trim,
        remove_thousand_separators=remove_thousand_separators,
        parentheses_negative=parentheses_negative,
        development_mode=development_mode,
    )

    try:
        expected_origins = generate_origin_sequence(origin_start, origin_end, grain)
        st.info(f"Expected origin periods: {', '.join(expected_origins)}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Origin period configuration error: {exc}")
        st.stop()

    parsed = parse_triangle_text(pasted_text, options)

    st.subheader("Validation and Parsing Messages")
    if parsed.validation.errors:
        for error in parsed.validation.errors:
            st.error(error)
    if parsed.validation.warnings:
        for warning in parsed.validation.warnings:
            st.warning(warning)

    if parsed.validation.errors:
        st.stop()

    st.success("Triangle parsed successfully.")

    st.subheader("Step 4: Triangle Preview")
    st.write(f"Standardized origins: {parsed.origin_labels}")
    st.write(f"Standardized development steps: {parsed.development_steps}")
    st.write(f"Triangle type: **{triangle_type}** | Value type: **{value_type}**")

    styled_triangle = parsed.wide_df.style.highlight_null(color="#ffe6e6")
    st.dataframe(styled_triangle, use_container_width=True)

    st.subheader("Step 5: Diagnostics and Reserving")

    initial_reserving = run_chain_ladder(parsed.wide_df, triangle_type)
    excluded = st.multiselect(
        "Exclude link ratio pairs from selected factors (sets factor to 1.0)",
        options=list(initial_reserving.selected_link_ratios.index),
        default=[],
    )
    reserving = run_chain_ladder(parsed.wide_df, triangle_type, excluded_pairs=excluded)
    diagnostics = build_diagnostics(reserving.cumulative_triangle, reserving.link_ratio_matrix)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Link Ratio Matrix**")
        st.dataframe(reserving.link_ratio_matrix, use_container_width=True)
        st.markdown("**Selected (Volume-weighted) Factors**")
        selected_compare = pd.DataFrame(
            {
                "all_average": initial_reserving.selected_link_ratios,
                "selected": reserving.selected_link_ratios,
            }
        )
        st.dataframe(selected_compare, use_container_width=True)

    with col2:
        st.markdown("**Maturity Summary**")
        st.dataframe(diagnostics.maturity_summary, use_container_width=True)
        st.markdown("**Outlier Flags (IQR method)**")
        st.dataframe(diagnostics.outlier_flags, use_container_width=True)

    st.markdown("**Missing Cell Map**")
    fig_missing = px.imshow(
        diagnostics.missing_map,
        labels={"x": "Development", "y": "Origin", "color": "Missing (1=yes)"},
        aspect="auto",
        title="Missingness Heatmap",
    )
    st.plotly_chart(fig_missing, use_container_width=True)

    st.markdown("**Reserving Summary (Latest, Ultimate, IBNR)**")
    st.dataframe(reserving.summary, use_container_width=True)

    st.subheader("Step 6: AI / Reporting Context")
    diagnostics_summary = {
        "maturity": diagnostics.maturity_summary.reset_index().to_dict(orient="records"),
        "missing_cells": int(diagnostics.missing_map.sum().sum()),
        "outlier_counts": diagnostics.outlier_flags.sum().to_dict(),
    }

    context = build_ai_context(options, parsed, reserving, diagnostics_summary)
    context_json = context_to_json(context)

    st.code(context_json, language="json")
    st.download_button(
        "Download AI Context JSON",
        data=context_json,
        file_name="triangle_ai_context.json",
        mime="application/json",
    )

    st.download_button(
        "Download Cleaned Triangle CSV",
        data=parsed.wide_df.to_csv(index=True),
        file_name="cleaned_triangle.csv",
        mime="text/csv",
    )
else:
    st.info("Configure periods and provide triangle input, then click 'Validate and Parse'.")
