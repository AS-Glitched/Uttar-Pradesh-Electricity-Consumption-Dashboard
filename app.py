# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd

from src.config import THEME, format_mw
from src.data_processor import load_data, build_filters, apply_filters
from src.analytics import (
    calculate_kpis, 
    detect_anomalies, 
    generate_insights,
    build_top_days_table,
    build_top_regions_table
)
from src.charts import (
    build_daily_trend, 
    build_monthly_average_chart, 
    build_yearly_trend, 
    build_seasonality_heatmap,
    build_forecast_chart
)
from src.map_builder import build_region_map

st.set_page_config(page_title="UrjaView: India Power Analytics", page_icon="⚡", layout="wide")

def apply_custom_css():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        :root {{
            --bg: {THEME['bg']};
            --sidebar-bg: {THEME['sidebar_bg']};
            --card-bg: {THEME['card_bg']};
            --accent: {THEME['primary_accent']};
            --accent-2: {THEME['secondary_accent']};
            --text: {THEME['text']};
            --muted: {THEME['muted']};
            --border: {THEME['border']};
        }}
        html, body, [data-testid="stAppViewContainer"], .stApp, .stMarkdown,
        .stTextInput input, .stSelectbox, .stMultiSelect, button {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        html, body, [data-testid="stAppViewContainer"] {{
            background: var(--bg);
            color: var(--text);
        }}
        [data-testid="stSidebar"] {{
            background: var(--sidebar-bg);
            border-right: 1px solid var(--border);
        }}
        .stApp {{ background: var(--bg); }}
        .block-container {{ padding-top: 1.5rem; padding-bottom: 1.5rem; }}
        [data-testid="stFileUploader"] {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 0.6rem;
        }}
        [data-testid="stFileUploader"] > section {{
            background: transparent;
            border: 1px dashed var(--border);
            border-radius: 14px;
        }}
        .stDownloadButton > button, .stButton > button {{
            background: linear-gradient(135deg, var(--accent) 0%, #2563eb 100%);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.55rem 0.9rem;
            font-weight: 600;
            box-shadow: 0 10px 20px rgba(59, 130, 246, 0.18);
            transition: all 0.2s ease;
        }}
        .stDownloadButton > button:hover, .stButton > button:hover {{
            filter: brightness(1.08);
            box-shadow: 0 12px 24px rgba(59, 130, 246, 0.28);
            transform: translateY(-1px);
        }}
        .stTextInput > div > div > input, .stSelectbox > div > div > div, .stMultiSelect > div > div > div {{
            background: var(--card-bg);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 10px;
        }}
        .stSidebar p, .stSidebar label, .stSidebar .stCheckbox {{ color: var(--muted); }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def style_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div style="margin-bottom: 1.25rem;">
            <h1 style="margin-bottom: 0.25rem; color:{THEME['text']}; font-size: 1.85rem; font-weight: 700;">{title}</h1>
            <p style="color:{THEME['muted']}; font-size: 0.98rem; margin-top: 0;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def metric_card(title: str, value: str, delta: str | None = None) -> None:
    delta_html = f"<div style='margin-top: 0.35rem; color:{THEME['secondary_accent']}; font-size: 0.92rem; font-weight: 600;'>{delta}</div>" if delta else ""
    st.markdown(
        f"""
        <div style="background: {THEME['card_bg']}; border: 1px solid {THEME['border']}; border-radius: 18px; padding: 0.95rem 1rem; box-shadow: 0 10px 24px rgba(2, 8, 23, 0.28); margin-bottom: 0.6rem; min-height: 100px;">
            <div style="font-size: 0.8rem; color: {THEME['muted']}; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.35rem;">{title}</div>
            <div style="font-size: 1.55rem; font-weight: 700; color: {THEME['text']}; margin-top: 0.2rem;">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_key_insights(df: pd.DataFrame) -> None:
    insights = generate_insights(df)
    if not insights:
        return
    bullet_points = "".join(f"<li style='margin-bottom:0.35rem;'>{insight}</li>" for insight in insights)
    st.markdown(
        f"""
        <div style="background: {THEME['card_bg']}; border: 1px solid {THEME['border']}; border-radius: 14px; padding: 0.8rem 0.95rem; margin-bottom: 0.9rem;">
            <div style="font-size: 0.76rem; color: {THEME['muted']}; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.3rem;">Key Insights</div>
            <ul style="margin: 0; padding-left: 1rem; color: {THEME['text']}; line-height: 1.45;">
                {bullet_points}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _render_non_geo_note(non_geo: pd.DataFrame) -> None:
    if non_geo.empty:
        return
    items = ", ".join(
        f"{row['region']} ({row['consumption_mw']:,.1f} MW)"
        for _, row in non_geo.iterrows()
    )
    st.caption(f"ℹ️ Non-geographic entities excluded from map: {items}")

def render_overview(df: pd.DataFrame) -> None:
    st.subheader("Consumption Overview")
    render_key_insights(df)
    
    kpis = calculate_kpis(df)
    daily = df.groupby("date")["consumption_mw"].sum().reset_index()
    anomalies = detect_anomalies(daily)
    anomaly_count = len(anomalies)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        metric_card("Average Daily", format_mw(kpis["avg_consumption"]))
    with col2:
        metric_card("Peak Daily", format_mw(kpis["peak_consumption"]))
    with col3:
        metric_card("Minimum Daily", format_mw(kpis["min_consumption"]))
    with col4:
        metric_card("Latest Daily", format_mw(kpis["latest_consumption"]))
    with col5:
        metric_card("Anomalies Found", str(anomaly_count), "In selected range")

    st.plotly_chart(build_daily_trend(df), use_container_width=True)
    
    chart1, chart2 = st.columns(2)
    with chart1:
        st.plotly_chart(build_monthly_average_chart(df), width="stretch")
    with chart2:
        st.plotly_chart(build_yearly_trend(df), width="stretch")

    map_fig, non_geo = build_region_map(df)
    st.plotly_chart(map_fig, width="stretch")
    _render_non_geo_note(non_geo)

def render_drill_down(df: pd.DataFrame, filters: dict) -> None:
    st.subheader("Drill-down Explorer")
    st.write("Refine the view by month, season, or a custom date range using the sidebar filters.")

    chart_col, side_col = st.columns([3, 1])
    with chart_col:
        if filters["view_by"] == "Daily":
            st.plotly_chart(build_daily_trend(df), width="stretch")
        elif filters["view_by"] == "Monthly":
            st.plotly_chart(build_monthly_average_chart(df), width="stretch")
        elif filters["view_by"] == "Seasonal":
            st.plotly_chart(build_seasonality_heatmap(df), width="stretch")
        else:
            st.plotly_chart(build_daily_trend(df), width="stretch")

    with side_col:
        st.subheader("Quick summary")
        kpis = calculate_kpis(df)
        metric_card("Average", format_mw(kpis["avg_consumption"]))
        metric_card("Peak", format_mw(kpis["peak_consumption"]))

    st.markdown("---")
    st.subheader("Anomaly Breakdown")
    daily = df.groupby("date")["consumption_mw"].sum().reset_index().sort_values("date")
    anomalies = detect_anomalies(daily)
    if anomalies.empty:
        st.success("No anomalies detected in this range.")
    else:
        st.warning(f"Detected {len(anomalies)} anomalies in the selected range.")
        display_df = anomalies[["date", "interpretation", "consumption_mw", "expected_value", "deviation_pct", "z_score"]].copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df["consumption_mw"] = display_df["consumption_mw"].round(2)
        display_df["expected_value"] = display_df["expected_value"].round(2)
        display_df["deviation_pct"] = display_df["deviation_pct"].round(2).astype(str) + "%"
        display_df["z_score"] = display_df["z_score"].round(2)
        
        display_df.columns = ["Date", "Type", "Actual (MW)", "Expected (MW)", "Deviation", "Z-Score"]
        st.dataframe(display_df, hide_index=True, width="stretch")

    bottom_col1, bottom_col2 = st.columns(2)
    with bottom_col1:
        st.caption("Top regions by consumption")
        st.dataframe(build_top_regions_table(df), width="stretch", hide_index=True)
    with bottom_col2:
        st.caption("Top consumption days")
        st.dataframe(build_top_days_table(df), width="stretch", hide_index=True)

def render_map_forecast(df: pd.DataFrame) -> None:
    st.subheader("Map & Forecasting")
    st.write("Visualize the geographic distribution across states and forecast future totals.")

    map_fig, non_geo = build_region_map(df)
    st.plotly_chart(map_fig, width="stretch")
    _render_non_geo_note(non_geo)
    
    st.plotly_chart(build_forecast_chart(df, periods=30), width="stretch")

def render_data_quality(df: pd.DataFrame, quality_report: dict) -> None:
    st.subheader("Data Quality Audit")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Rows after cleaning", f"{quality_report['row_count_after']:,}")
    with col2:
        metric_card("Duplicates removed", f"{quality_report['duplicate_count_before']:,}")
    with col3:
        metric_card("Date range", f"{quality_report['date_range']['start']} → {quality_report['date_range']['end']}")
    with col4:
        metric_card("Invalid negatives", f"{quality_report.get('invalid_negative_count', 0):,}")

    st.write("### Cleaning steps")
    for step in quality_report["cleaning_steps"]:
        st.write(f"- {step}")

def render_downloads(filtered_df: pd.DataFrame, cleaned_df: pd.DataFrame, summary_text: str) -> None:
    st.sidebar.markdown("### Exports")
    st.sidebar.download_button(
        label="Download Filtered Data (CSV)",
        data=filtered_df.to_csv(index=False),
        file_name="india_electricity_filtered.csv",
        mime="text/csv",
    )
    st.sidebar.download_button(
        label="Download Insight Summary (TXT)",
        data=summary_text,
        file_name="india_electricity_summary.txt",
        mime="text/plain",
    )

def main() -> None:
    apply_custom_css()
    
    st.sidebar.title("⚡ UrjaView")
    st.sidebar.caption("India Power Analytics Dashboard")
    st.sidebar.markdown("---")

    uploaded_file = st.sidebar.file_uploader("Upload custom CSV", type=["csv"])

    try:
        df, quality_report = load_data(uploaded_file)
    except Exception as exc:
        st.error(f"Error loading data: {exc}")
        st.stop()

    filters = build_filters(df)
    filtered_df = apply_filters(df, filters)

    style_header(
        "India Electricity Consumption Dashboard",
        "Interactive analytics and forecasting of power consumption across Indian states.",
    )

    if filtered_df.empty:
        st.info("The selected filters returned no data. Please adjust the sidebar filters.")
        return

    render_downloads(filtered_df, df, "\n".join(generate_insights(filtered_df)))

    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Drill-down Explorer", "Map & Forecast", "Data Quality"],
        index=0,
    )
    
    if page == "Overview":
        render_overview(filtered_df)
    elif page == "Drill-down Explorer":
        render_drill_down(filtered_df, filters)
    elif page == "Map & Forecast":
        render_map_forecast(filtered_df)
    else:
        render_data_quality(filtered_df, quality_report)

    st.markdown(
        f"""
        <div style="margin-top: 2rem; padding: 1rem; border-top: 1px solid {THEME['border']}; color:{THEME['muted']}; font-size:0.85rem; text-align: center;">
            UrjaView: India Power Analytics • Built with Streamlit & Plotly
        </div>
        """,
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
