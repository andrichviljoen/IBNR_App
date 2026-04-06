import pandas as pd

from services.grid_input import grid_dataframe_to_tsv


def test_grid_dataframe_to_tsv_preserves_blanks_and_text():
    df = pd.DataFrame(
        [
            ["", "0", "12"],
            ["2019", 100, "abc"],
            ["2020", "", 200],
        ]
    )
    output = grid_dataframe_to_tsv(df)
    assert output.splitlines()[0] == "\t0\t12"
    assert output.splitlines()[1] == "2019\t100\tabc"
    assert output.splitlines()[2] == "2020\t\t200"


def test_grid_dataframe_to_tsv_empty_result():
    df = pd.DataFrame([["", ""], ["", ""]])
    assert grid_dataframe_to_tsv(df) == ""
