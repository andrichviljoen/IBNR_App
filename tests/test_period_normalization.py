from services.development_periods import normalize_development_headers
from services.origin_periods import generate_origin_sequence, normalize_origin_label


def test_origin_normalization_quarterly():
    assert normalize_origin_label("2020-Q1", "Quarterly") == "2020Q1"
    assert normalize_origin_label("2020/05/01", "Quarterly") == "2020Q2"


def test_origin_sequence_semi_annual():
    seq = generate_origin_sequence("2020H1", "2021H2", "Semi-Annual")
    assert seq == ["2020H1", "2020H2", "2021H1", "2021H2"]


def test_development_normalization_elapsed_months_annual():
    steps, labels = normalize_development_headers(["0", "12", "24"], "Annual", "elapsed_months")
    assert steps == [0, 1, 2]
    assert labels == ["Dev 0", "Dev 1", "Dev 2"]
