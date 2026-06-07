import streamlit as st
import polars as pl
import httpx
from datetime import datetime
from charts.plots import (
    chart_temp_trends, chart_humidity_heatmap,
    chart_rainfall_bar, chart_city_snapshot,
    chart_temp_distribution, chart_comparison_bar,
    chart_forecast_panel
)
from processing.analysis import fetch_all_latest, city_comparison

# Page config
st.set_page_config(
    page_title= "Nepal Weather Dashboard",
    page_icon= "🌤️",
    layout= "wide",
    initial_sidebar_state= "expanded",
)

# Sidebar Controls
with st.sidebar:
    st.title("Nepal Weather")
    st.caption("Real-time weather for Nepali cities")
    st.divider()

    days = st.slider("History (days)", 1, 30, 7)
    selected_city = st.selectbox(
        "City for forecast",
        ["Dharan", "Kathmandu", "Pokhara",
         "Biratnagar", "Butwal"],
    )
    
    if st.button("Scrape now", type="primary"):
        with st.spinner("Scraping..."):
            try:
                resp = httpx.post(
                    "http://localhost:8000/weather/scrape"
                )
                result = resp.json()
                st.success(
                    f"Saved {result['saved']} readings"
                )
            except Exception as e:
                st.error(f"Error: {e}")
    
    st.divider()
    st.caption(f"Last updated: {datetime.now():%H:%M:%S}")

# Header metric cards
st.title("Nepal Weather Dashboard")

try:
    latest_df = fetch_all_latest()
    if not latest_df.is_empty():
        # Show one metric card per city
        cols = st.columns(len(latest_df))
        for col, row in zip(cols,
                             latest_df.iter_rows(named=True)):
            with col:
                st.metric(
                    label = row["city"],
                    value = f"{row['temp_c']:.1f}°C",
                    delta = f"{row['humidity']}% humidity",
                )
        st.caption(
            f"Wind: " +
            "  |  ".join(
                f"{r['city']}: {r['wind_speed']:.1f} m/s"
                for r in latest_df.iter_rows(named=True)
            )
        )
except Exception as e:
    st.warning(f"Could not load latest readings: {e}")

st.divider()

# Tab layout
tab1, tab2, tab3, tab4 = st.tabs([
    "Temperature",
    "Rainfall & Humidity",
    "Comparison",
    "Forecast",
])

with tab1:
    st.subheader(f"Temperature Trends — last {days} days")
    st.plotly_chart(
        chart_temp_trends(days),
        use_container_width=True,
    )
    st.subheader("Temperature Distribution")
    st.plotly_chart(
        chart_temp_distribution(days),
        use_container_width=True,
    )

with tab2:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Humidity Heatmap")
        st.plotly_chart(
            chart_humidity_heatmap(days),
            use_container_width=True,
        )
    with col2:
        st.subheader(f"Rainfall — last {days} days")
        st.plotly_chart(
            chart_rainfall_bar(days),
            use_container_width=True,
        )

with tab3:
    st.subheader("City Snapshot — Current Conditions")
    st.plotly_chart(
        chart_city_snapshot(),
        use_container_width=True,
    )
    st.subheader("City Comparison — Last 24 Hours")
    st.plotly_chart(
        chart_comparison_bar(),
        use_container_width=True,
    )
    st.subheader("Summary Table")
    try:
        df = city_comparison(days)
        st.dataframe(
            df.to_pandas(),
            use_container_width=True,
            hide_index=True,
        )
    except Exception:
        pass

with tab4:
    st.subheader(f"5-Day Forecast — {selected_city}")
    st.plotly_chart(
        chart_forecast_panel(selected_city),
        use_container_width=True,
    )
    
# Raw data expander
with st.expander("Raw data — download CSV"):
    try:
        resp = httpx.get(
            "http://localhost:8000/weather/history",
            params={"city": selected_city, "days": days},
        )
        if resp.status_code == 200:
            df_raw = pl.DataFrame(resp.json())
            st.dataframe(df_raw.to_pandas(),
                          use_container_width=True)
            st.download_button(
                label   = f"Download {selected_city} CSV",
                data    = df_raw.write_csv(),
                file_name = f"{selected_city}_weather.csv",
                mime    = "text/csv",
            )
    except Exception as e:
        st.error(str(e))
