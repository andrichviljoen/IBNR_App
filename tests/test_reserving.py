import numpy as np

from services.reserving_calculations import ensure_cumulative, latest_diagonal, run_chain_ladder


def test_incremental_to_cumulative_conversion():
    import pandas as pd

    incremental = pd.DataFrame({0: [100, 120], 1: [50, 60], 2: [25, np.nan]}, index=["2020", "2021"])
    cumulative = ensure_cumulative(incremental, "Incremental")
    assert cumulative.loc["2020", 2] == 175


def test_latest_diagonal_extraction():
    import pandas as pd

    triangle = pd.DataFrame({0: [100, 120], 1: [150, 180], 2: [175, np.nan]}, index=["2020", "2021"])
    diag = latest_diagonal(triangle)
    assert diag.loc["2020"] == 175
    assert diag.loc["2021"] == 180


def test_end_to_end_ibnr_total_known_triangle():
    import pandas as pd

    triangle = pd.DataFrame(
        {
            0: [100.0, 120.0, 140.0],
            1: [150.0, 180.0, np.nan],
            2: [180.0, np.nan, np.nan],
        },
        index=["2019", "2020", "2021"],
    )

    result = run_chain_ladder(triangle, "Cumulative")
    assert result.summary.loc["Total", "ibnr"] > 0
    assert result.summary.loc["2019", "ibnr"] == 0
