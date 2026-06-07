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

def chart_rainfall_bar(days: int = 30) -> go.Figure:
    """Grouped bar chart — total rainfall per city per day."""
    fig = go.Figure()
    for city in CITIES:
        try:
            df    = fetch_history(city, days)
            daily = daily_summary(df)
            fig.add_trace(go.Bar(
                x    = daily["date"].to_list(),
                y    = daily["total_rain"].to_list(),
                name = city,
                marker_color = CITY_COLORS[city],
                opacity      = 0.8,
                hovertemplate=(
                    f"{city}"
                    "Date: %{x}"
                    "Rain: %{y:.2f} mm"
                ),
            ))
        except Exception:
            pass
    fig.update_layout(
        barmode     = "group",
        title       = f"Daily Rainfall — Last {days} Days",
        xaxis_title = "Date",
        yaxis_title = "Total Rainfall (mm)",
        legend      = dict(orientation="h", y=-0.2),
        margin      = dict(l=40, r=20, t=50, b=80),
    )
    return fig

def chart_city_snapshot() -> go.Figure:
    """
    4-metric snapshot — latest reading per city.
    Polar/radar chart: unusual chart type that stands out
    in a portfolio and looks genuinely professional.
    """
    df = fetch_all_latest()
    if df.is_empty():
        return go.Figure()

    metrics = ["temp_c", "humidity", "wind_speed", "rain_1h"]
    labels  = ["Temp (°C)", "Humidity (%)",
               "Wind (m/s)", "Rain (mm)"]
    fig = go.Figure()

    for row in df.iter_rows(named=True):
        city   = row.get("city", "?")
        values = [row.get(m, 0) for m in metrics]
        values += [values[0]]   # close the loop
        fig.add_trace(go.Scatterpolar(
            r    = values,
            theta= labels + [labels[0]],
            fill = "toself",
            name = city,
            line = dict(color=CITY_COLORS.get(city, "#888")),
            opacity = 0.6,
        ))
    fig.update_layout(
        title        = "Current Weather Snapshot — All Cities",
        polar        = dict(radialaxis=dict(visible=True)),
        showlegend   = True,
        margin       = dict(l=60, r=60, t=60, b=60),
    )
    return fig

def chart_temp_distribution(days: int = 7) -> go.Figure:
    """
    Violin plot — shows full temperature distribution per city.
    Better than a box plot: shows the actual shape of the data.
    """
    frames = []
    for city in CITIES:
        try:
            df = fetch_history(city, days)
            for t in df["temp_c"].to_list():
                frames.append({"city": city, "temp_c": t})
        except Exception:
            pass

    df_all = pl.DataFrame(frames)
    if df_all.is_empty():
        return go.Figure()

    fig = px.violin(
        df_all.to_pandas(),
        x           = "city",
        y           = "temp_c",
        color       = "city",
        color_discrete_map = CITY_COLORS,
        box         = True,
        points      = "outliers",
        title       = f"Temperature Distribution — Last {days} Days",
        labels      = {"temp_c": "Temperature (°C)",
                       "city":   "City"},
    )
    fig.update_layout(showlegend=False,
                       margin=dict(l=40, r=20, t=50, b=40))
    return fig

def chart_forecast_panel(city: str = "Dharan") -> go.Figure:
    """
    Two-panel forecast: temperature band + rainfall bars.
    Uses make_subplots — Plotly's equivalent of matplotlib subplots.
    """
    import httpx
    resp = httpx.get(f"http://localhost:8000/forecast/{city}")
    if resp.status_code != 200:
        return go.Figure()
    data = resp.json()
    df   = pl.DataFrame(data)
    if df.is_empty():
        return go.Figure()

    color = CITY_COLORS.get(city, "#378ADD")
    fig   = make_subplots(
        rows=2, cols=1,
        shared_xaxes  = True,
        subplot_titles= ("Temperature Forecast", "Rainfall"),
        vertical_spacing = 0.12,
        row_heights   = [0.7, 0.3],
    )
    # Temperature band
    fig.add_trace(go.Scatter(
        x=df["forecast_for"].to_list(),
        y=df["temp_max"].to_list(),
        fill=None, mode="lines",
        line=dict(width=0),
        name="Max temp", showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df["forecast_for"].to_list(),
        y=df["temp_min"].to_list(),
        fill="tonexty", mode="lines",
        fillcolor=f"rgba({int(color[1:3],16)},"
                  f"{int(color[3:5],16)},"
                  f"{int(color[5:7],16)},0.15)",
        line=dict(width=0),
        name="Temp range",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df["forecast_for"].to_list(),
        y=df["temp_c"].to_list(),
        line=dict(color=color, width=2),
        name="Forecast temp",
    ), row=1, col=1)
    # Rainfall bars
    fig.add_trace(go.Bar(
        x=df["forecast_for"].to_list(),
        y=df["rain_3h"].to_list(),
        marker_color=color, opacity=0.7,
        name="Rain (mm/3h)",
    ), row=2, col=1)
    fig.update_layout(
        title  = f"5-Day Forecast — {city}",
        margin = dict(l=40, r=20, t=70, b=40),
    )
    return fig

def chart_comparison_bar() -> go.Figure:
    """Horizontal bar comparison — latest snapshot all metrics."""
    df = fetch_stats(days=1)
    if df.is_empty():
        return go.Figure()

    metrics = [
        ("avg_temp",     "Avg Temp (°C)"),
        ("avg_humidity", "Humidity (%)"),
        ("total_rain",   "Rain (mm)"),
    ]
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=[m[1] for m in metrics],
    )
    for col_idx, (metric, label) in enumerate(metrics, 1):
        fig.add_trace(go.Bar(
            y           = df["city"].to_list(),
            x           = df[metric].to_list(),
            orientation = "h",
            marker_color= [CITY_COLORS.get(c, "#888")
                            for c in df["city"].to_list()],
            showlegend  = False,
            name        = label,
        ), row=1, col=col_idx)
    fig.update_layout(
        title  = "City Comparison — Last 24 Hours",
        height = 300,
        margin = dict(l=80, r=20, t=70, b=40),
    )
    return fig