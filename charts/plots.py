import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl
from processing.analysis import (
    fetch_history, fetch_all_latest,
    daily_summary, temperature_trend,
    city_comparison, fetch_stats
)

CITY_COLORS = {
    "Dharan":     "#378ADD",
    "Kathmandu":  "#1D9E75",
    "Pokhara":    "#534AB7",
    "Biratnagar": "#D85A30",
    "Butwal":     "#BA7517",
}

CITIES = list(CITY_COLORS.keys())

def chart_temp_trends(days: int = 7) -> go.Figure:
    """ 
    Multi-city temperature time series.
    Plotly: hover shows exact value, zoom with mouse scroll,
    click legend items to toggle city on/off.
    matplotlib could not do any of this without extra libraries.
    """
    fig = go.Figure()
    for city in CITIES:
        try:
            df = fetch_history(city, days)
            df = temperature_trend(df)
            fig.add_trace(go.Scatter(
                x = df["timestamp"].to_list(),
                y = df["temp_rolling_avg"].to_list(),
                name= city,
                line= dict(color=CITY_COLORS[city], width=2),
                hovertemplate=(
                    f"{city}"
                    
                    "Time: %{x}"
                    
                    "Temp: %{y:.1f}°C"
                ),
            ))
        except Exception:
            pass
    fig.update_layout(
        title = "Temperature Trends (6-hr rolling avg)",
        xaxis_title = "Date",
        yaxis_title = "Temperature (°C)",
        hovermode = "x unified",
        legend = dict(orientation="h", y=-0.15),
        margin = dict(l=40, r=20, t=50, b=60),
    )
    return fig

def chart_humidity_heatmap(days: int = 7) -> go.Figure:
    """ 
    Heatmap - city vs day, color = avg humidity.
    Interactive: hover to see exact value, zoom on dates
    """
    frames = []
    for city in CITIES:
        try:
            df = fetch_history(city, days)
            daily = daily_summary(df)
            for row in daily.iter_rows(named=True):
                frames.append({
                    "city": city,
                    "date": str(row["date"]),
                    "humidity": row["avg_humidity"],
                })
        except Exception:
            pass
    df_all = pl.DataFrame(frames)
    if df_all.is_empty():
        return go.Figure()
    
    pivot = df_all.pivot(
        index="city", columns= "date",
        values="humidity", aggregate_function="mean"
    )
    dates = [c for c in pivot.columns if c != "city"]
    cities = pivot["city"].to_list()
    z = pivot.select(dates).to_numpy()

    fig = go.Figure(go.Heatmap(
        x = dates,
        y = cities,
        z = z,
        colorscale= "YlOrRd",
        colorbar= dict(title="Humidity %"),
        hovertemplate=(
            "City: %{y}"
            "Date: %{x}"
            "Humidity: %{z:.0f}%"
        ),
    ))
    fig.update_layout(
        title = "Average Daily Humidity by City",
        margin = dict(l = 100, r=20, t=50, b=60),
    )
    return fig