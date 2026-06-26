import polars as pl
import pytest
from processing.analysis import daily_summary, detect_anomalies

def make_sample_df() -> pl.DataFrame:
    return pl.DataFrame({
        "city":      ["Dharan"] * 6,
        "timestamp": [
            "2024-01-01T06:00:00", "2024-01-01T12:00:00",
            "2024-01-01T18:00:00", "2024-01-02T06:00:00",
            "2024-01-02T12:00:00", "2024-01-02T18:00:00",
        ],
        "temp_c":    [22.0, 28.0, 26.0, 23.0, 29.0, 27.0],
        "humidity":  [75, 65, 70, 78, 63, 68],
        "rain_1h":   [0.0, 0.5, 0.0, 1.2, 0.0, 0.3],
        "wind_speed":[2.1, 3.5, 2.8, 1.9, 4.2, 3.1],
    })

def test_daily_summary_aggregates_correctly():
    df    = make_sample_df()
    daily = daily_summary(df)
    assert len(daily) == 2   # 2 distinct dates
    day1  = daily.filter(
        pl.col("date") == pl.date(2024, 1, 1)
    )
    assert day1["avg_temp"][0] == pytest.approx(
        (22.0 + 28.0 + 26.0) / 3, rel=0.01
    )
    assert day1["total_rain"][0] == pytest.approx(0.5)

def test_daily_summary_max_min():
    df    = make_sample_df()
    daily = daily_summary(df)
    day1  = daily.filter(
        pl.col("date") == pl.date(2024, 1, 1)
    )
    assert day1["max_temp"][0] == 28.0
    assert day1["min_temp"][0] == 22.0

def test_detect_anomalies_returns_dataframe():
    df      = make_sample_df()
    anomalies = detect_anomalies(df, sigma=0.5)
    # With sigma=0.5, some readings should be flagged
    assert isinstance(anomalies, pl.DataFrame)
    assert "is_anomaly" in anomalies.columns

def test_empty_dataframe_handled():
    empty = pl.DataFrame({
        "city": [], "timestamp": [],
        "temp_c": pl.Series([], dtype=pl.Float64),
        "humidity": pl.Series([], dtype=pl.Int64),
        "rain_1h": pl.Series([], dtype=pl.Float64),
        "wind_speed": pl.Series([], dtype=pl.Float64),
    })
    daily = daily_summary(empty)
    assert daily.is_empty()