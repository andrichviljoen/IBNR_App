import numpy as np

from services.triangle_parser import ParseOptions, parse_triangle_text, split_pasted_grid


BASE_OPTIONS = ParseOptions(
    grain="Annual",
    origin_start="2019",
    origin_end="2022",
    triangle_type="Cumulative",
    value_type="Incurred",
)


def test_split_pasted_grid_tab_delimited():
    text = "\t0\t12\n2019\t100\t150\n2020\t200\t"
    rows = split_pasted_grid(text)
    assert rows[0] == ["", "0", "12"]
    assert rows[2] == ["2020", "200", ""]


def test_parse_triangle_preserves_blank_as_nan():
    text = "\t0\t12\n2019\t100\t150\n2020\t200\t"
    parsed = parse_triangle_text(text, BASE_OPTIONS)
    assert parsed.validation.is_valid
    assert np.isnan(parsed.wide_df.loc["2020", 12])


def test_parse_triangle_blank_as_zero():
    options = ParseOptions(**{**BASE_OPTIONS.__dict__, "blank_as_zero": True})
    text = "\t0\t12\n2019\t100\t150\n2020\t200\t"
    parsed = parse_triangle_text(text, options)
    assert parsed.validation.is_valid
    assert parsed.wide_df.loc["2020", 12] == 0.0


def test_invalid_numeric_cell_raises_validation_error():
    text = "\t0\t12\n2019\t100\tabc\n2020\t200\t220"
    parsed = parse_triangle_text(text, BASE_OPTIONS)
    assert any("Invalid numeric value" in e for e in parsed.validation.errors)
