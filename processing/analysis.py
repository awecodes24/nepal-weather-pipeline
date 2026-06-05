import polars as pl
import httpx
from datetime import datetime, timedelta

API_BASE = "http://localhost:8000"

def fetch_history(city: str, days: int = 7) -> pl.DataFrame:
    """Fetch history from FastAPI and load into Polars DataFrame."""
    resp = httpx.get(f"{API_BASE}/weather/history",
                     params={"city": city, "days": days})
    resp.raise_for_status()
    return pl.DataFrame(resp.json())

def fetch_all_latest() -> pl.DataFrame:
    resp = httpx.get(f"{API_BASE}/weather/latest")
    resp.raise_for_status()
    return pl.DataFrame(resp.json())

def fetch_stats(days: int = 7) -> pl.DataFrame:
    resp = httpx.get(f"{API_BASE}/weather/stats",
                     params={"days": days})
    resp.raise_for_status()
    return pl.DataFrame(resp.json())

    
# Polars transforms

def daily_summary(df: pl.DataFrame) -> pl.DataFrame:
    """ 
    Aggregate hourly readings into daily stats.
    Polars equivalent of pandas groupby + agg, but faster.
    """
    return (
        df
        .with_columns(
            pl.col("timestamp")
              .str.to_datetime()
              .dt.date()
              .alias("date")
        )
        .group_by("date", "city")
        .agg([
            pl.col("temp_c").mean().round(1).alias("avg_temp"),
            pl.col("temp_c").max().alias("max_temp"),
            pl.col("temp_c").min().alias("min_temp"),
            pl.col("humidity").mean().round(0).alias("avg_humidity"),
            pl.col("rain_1h").sum().round(2).alias("total_rain"),
            pl.col("wind_speed").mean().round(1).alias("avg_wind"),
        ])
        .sort("date")
    )
    
def temperature_trend(df: pl.DataFrame) -> pl.DataFrame:
    """
    Rolling 6-hour moving average for temperature.
    Polars lazy API: .lazy() → chain → .collect()
    Nothing executes until .collect() — Polars optimises the
    whole query plan before touching data.
    """
    return (
        df.lazy()
          .with_columns(
              pl.col("timestamp").str.to_datetime()
          )
          .sort("timestamp")
          .with_columns(
              pl.col("temp_c")
                .rolling_mean(window_size=6)
                .alias("temp_rolling_avg")
          )
          .collect()
    )

def humidity_pivot(df: pl.DataFrame) -> pl.DataFrame:
    """ 
    Pivot: rows=city, columns=date, values=avg_humidity.
    Used by the heatmap chart.
    """
    daily = daily_summary(df)
    return daily.pivot(
        index= "city", 
        columns= "date",
        values= "avg_humidity",
        aggregate_function="mean",
    )
    
def city_comparison(days: int = 7) -> pl.DataFrame:
    """ 
    Fetch stats for all cities and return a comparison table.
    Shows how concise Polars is - no for loops, just expressions.
    """
    return (
        fetch_stats(days)
        .with_columns([
            pl.col("avg_temp").round(1),
            pl.col("avg_humidity").round(0),
            pl.col("total_rain").round(2),
        ])
        .sort("avg_temp", descending=True)
    )
    
def detect_anomalies(df: pl.DataFrame,
                     sigma: float = 2.0) -> pl.DataFrame:
    """ 
    Flag temperature readings more than N standard deviations
    from the rolling mean - simple anomaly detection.
    """
    return (
        df.lazy()
          .sort("timestamp")
          .with_columns([
              pl.col("temp_c").mean().over("city")
                .alias("city_mean"),
              pl.col("temp_c").std().over("city")
                .alias("city_std"),
          ])
          .with_columns(
              (
                  (pl.col("temp_c") - pl.col("city_mean")).abs()
                  > sigma * pl.col("city_std")
              ).alias("is_anomaly")
          )
          .filter(pl.col("is_anomaly"))
          .collect()
    )