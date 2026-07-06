import re
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Use the workspace `data/UP_electricity_consumption.csv` by default if present
DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "UP_electricity_consumption.csv"

THEME = {
    "bg": "#0F172A",
    "sidebar_bg": "#111827",
    "card_bg": "#1E293B",
    "primary_accent": "#3B82F6",
    "secondary_accent": "#14B8A6",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "border": "#334155",
}
MONTH_ORDER = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

st.set_page_config(page_title="Uttar Pradesh Electricity Consumption Dashboard", page_icon="⚡", layout="wide")

st.markdown(
    f"""
    <style>
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
    html, body, [data-testid="stAppViewContainer"] {{
        background: var(--bg);
        color: var(--text);
    }}
    [data-testid="stSidebar"] {{
        background: var(--sidebar-bg);
        border-right: 1px solid var(--border);
    }}
    .stApp {{ background: var(--bg); }}
    .block-container {{ padding-top: 1.8rem; padding-bottom: 1.8rem; }}
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
        box-shadow: 0 10px 20px rgba(59, 130, 246, 0.18);
    }}
    .stDownloadButton > button:hover, .stButton > button:hover {{
        filter: brightness(1.05);
        box-shadow: 0 12px 24px rgba(59, 130, 246, 0.24);
    }}
    .stTextInput > div > div > input, .stSelectbox > div > div > div, .stMultiSelect > div > div > div {{
        background: var(--card-bg);
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: 10px;
    }}
    .stSidebar p, .stSidebar label, .stSidebar .stCheckbox {{ color: var(--muted); }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 0.5rem; }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 999px;
        background: var(--card-bg);
        color: var(--muted);
        border: 1px solid var(--border);
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, var(--accent) 0%, #2563eb 100%);
        color: white;
        border-color: var(--accent);
    }}
    .block-container {{ padding-top: 1rem; padding-bottom: 1rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def normalize_column_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def format_mw(value: float) -> str:
    return f"{value:,.2f} MW"


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


def load_data(uploaded_file=None) -> tuple[pd.DataFrame, dict]:
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
    elif DEFAULT_DATA_PATH.exists():
        data = pd.read_csv(DEFAULT_DATA_PATH)
    else:
        raise ValueError("No energy dataset was found. Please upload a CSV file with energy data.")

    quality_report = {
        "source": "uploaded" if uploaded_file is not None else "sample",
        "row_count_before": len(data),
        "duplicate_count_before": int(data.duplicated().sum()),
        "missing_values_before": data.isna().sum().to_dict(),
        "dtypes_before": {col: str(dtype) for col, dtype in data.dtypes.items()},
        "invalid_numeric_rows": {},
        "cleaning_steps": [],
    }

    date_column = next((col for col in data.columns if normalize_column_name(col) == "dates"), None)
    up_column = next((col for col in data.columns if normalize_column_name(col) == "up"), None)

    if not date_column or not up_column:
        raise ValueError("The file must contain a Dates column and a UP column.")

    data = data[[date_column, up_column]].copy()
    data.columns = ["date", "consumption_mw"]

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    original = data["consumption_mw"].copy()
    data["consumption_mw"] = pd.to_numeric(data["consumption_mw"], errors="coerce")
    quality_report["invalid_numeric_rows"]["consumption_mw"] = int(original.notna().sum() - data["consumption_mw"].notna().sum())
    data = data.dropna().reset_index(drop=True)

    if data.empty:
        raise ValueError("No valid Uttar Pradesh consumption rows were found.")

    data["year"] = data["date"].dt.year
    data["month"] = data["date"].dt.month
    data["month_name"] = data["date"].dt.month_name()

    quality_report["row_count_after"] = len(data)
    quality_report["duplicate_count_after"] = int(data.duplicated().sum())
    quality_report["missing_values_after"] = data.isna().sum().to_dict()
    quality_report["date_range"] = {
        "start": data["date"].min().strftime("%Y-%m-%d"),
        "end": data["date"].max().strftime("%Y-%m-%d"),
    }
    quality_report["cleaning_steps"] = [
        "Loaded the Dates and UP columns only",
        "Parsed the date column into datetime format",
        "Converted consumption values to numeric format",
        "Dropped missing values and added year/month fields",
    ]
    return data, quality_report


def build_filters(df: pd.DataFrame) -> dict:
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    st.sidebar.header("Filters")

    preset = st.sidebar.selectbox(
        "Quick range",
        ["All time", "Last 30 days", "Last 90 days", "Last 365 days", "Custom"],
        index=0,
    )

    if preset == "Last 30 days":
        start_date = max_date - timedelta(days=29)
        end_date = max_date
    elif preset == "Last 90 days":
        start_date = max_date - timedelta(days=89)
        end_date = max_date
    elif preset == "Last 365 days":
        start_date = max_date - timedelta(days=364)
        end_date = max_date
    elif preset == "Custom":
        start_date = st.sidebar.date_input("Start date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.sidebar.date_input("End date", max_date, min_value=min_date, max_value=max_date)
    else:
        start_date = min_date
        end_date = max_date

    available_years = sorted(df["year"].unique().tolist())
    available_months = [m for m in MONTH_ORDER if m in df["month_name"].unique()]

    selected_years = st.sidebar.multiselect("Year", available_years, default=available_years)
    selected_months = st.sidebar.multiselect("Month", available_months, default=available_months)

    return {
        "start_date": pd.Timestamp(start_date),
        "end_date": pd.Timestamp(end_date),
        "years": selected_years,
        "months": selected_months,
    }


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    filtered = df.copy()
    filtered = filtered[(filtered["date"] >= filters["start_date"]) & (filtered["date"] <= filters["end_date"])]
    if filters["years"]:
        filtered = filtered[filtered["year"].isin(filters["years"])]
    if filters["months"]:
        filtered = filtered[filtered["month_name"].isin(filters["months"])]
    return filtered


def calculate_kpis(df: pd.DataFrame) -> dict:
    avg_consumption = float(df["consumption_mw"].mean())
    peak_consumption = float(df["consumption_mw"].max())
    min_consumption = float(df["consumption_mw"].min())
    latest_consumption = float(df.sort_values("date").iloc[-1]["consumption_mw"])
    return {
        "avg_consumption": avg_consumption,
        "peak_consumption": peak_consumption,
        "min_consumption": min_consumption,
        "latest_consumption": latest_consumption,
    }


def build_daily_trend(df: pd.DataFrame) -> go.Figure:
    df_sorted = df.sort_values("date").copy()
    df_sorted["rolling_avg_30d"] = df_sorted["consumption_mw"].rolling(window=30, min_periods=30).mean()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_sorted["date"],
            y=df_sorted["consumption_mw"],
            mode="lines+markers",
            name="Daily Consumption",
            line=dict(color=THEME["primary_accent"], width=1.4),
            opacity=0.45,
            marker=dict(size=3, color=THEME["primary_accent"]),
            hovertemplate="%{x|%b %d, %Y}<br>%{y:,.2f} MW<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_sorted["date"],
            y=df_sorted["rolling_avg_30d"],
            mode="lines",
            name="30-Day Rolling Avg",
            line=dict(color=THEME["secondary_accent"], width=2.6),
            hovertemplate="%{x|%b %d, %Y}<br>%{y:,.2f} MW<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        title="Daily Consumption Trend",
        margin=dict(l=10, r=10, t=40, b=10),
        height=300,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        xaxis_title="Date",
        yaxis_title="MW",
        legend_title_text="",
    )
    return fig


def build_monthly_average_chart(df: pd.DataFrame) -> go.Figure:
    monthly = (
        df.assign(month_name=pd.Categorical(df["month_name"], categories=MONTH_ORDER, ordered=True))
        .groupby("month_name", observed=True)["consumption_mw"]
        .mean()
        .reset_index()
    )
    fig = px.bar(
        monthly,
        x="month_name",
        y="consumption_mw",
        text_auto=".1f",
        color_discrete_sequence=[THEME["secondary_accent"]],
    )
    fig.update_layout(
        template="plotly_dark",
        title="Monthly Average Consumption",
        margin=dict(l=10, r=10, t=40, b=10),
        height=300,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        xaxis_title="Month",
        yaxis_title="Average MW",
    )
    fig.update_traces(hovertemplate="%{x}<br>%{y:,.2f} MW<extra></extra>")
    return fig


def build_yearly_trend(df: pd.DataFrame) -> go.Figure:
    yearly = df.groupby("year")["consumption_mw"].sum().reset_index()
    fig = px.line(
        yearly,
        x="year",
        y="consumption_mw",
        markers=True,
        color_discrete_sequence=[THEME["primary_accent"]],
    )
    fig.update_layout(
        template="plotly_dark",
        title="Yearly Consumption Trend",
        margin=dict(l=10, r=10, t=40, b=10),
        height=300,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        xaxis_title="Year",
        yaxis_title="Total MW",
    )
    fig.update_traces(hovertemplate="%{x}<br>%{y:,.2f} MW<extra></extra>")
    return fig


def build_seasonality_heatmap(df: pd.DataFrame) -> go.Figure:
    pivot = (
        df.assign(month_name=pd.Categorical(df["month_name"], categories=MONTH_ORDER, ordered=True))
        .pivot_table(index="year", columns="month_name", values="consumption_mw", aggfunc="mean")
        .reindex(columns=MONTH_ORDER)
        .fillna(0)
    )
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="Blues",
            colorbar=dict(title="Average MW"),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        title="Seasonality: Month vs Year",
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        xaxis_title="Month",
        yaxis_title="Year",
    )
    return fig


def build_top_days_table(df: pd.DataFrame) -> pd.DataFrame:
    top_days = (
        df[["date", "consumption_mw"]]
        .sort_values("consumption_mw", ascending=False)
        .head(10)
        .copy()
    )
    top_days["date"] = top_days["date"].dt.strftime("%Y-%m-%d")
    top_days["consumption_mw"] = top_days["consumption_mw"].round(2)
    top_days.columns = ["Date", "Consumption (MW)"]
    return top_days


def generate_insights(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []

    peak_record = df.loc[df["consumption_mw"].idxmax()]
    min_record = df.loc[df["consumption_mw"].idxmin()]
    monthly_avg = df.groupby("month_name")["consumption_mw"].mean().sort_values(ascending=False)
    highest_month = monthly_avg.index[0]
    lowest_month = monthly_avg.index[-1]

    insights = [
        f"Peak consumption occurred on {peak_record['date'].strftime('%b %d, %Y')} at {format_mw(float(peak_record['consumption_mw']))}.",
        f"The lowest observed consumption was on {min_record['date'].strftime('%b %d, %Y')} at {format_mw(float(min_record['consumption_mw']))}.",
        f"{highest_month} shows the highest average monthly consumption, while {lowest_month} is the lowest.",
    ]
    return insights


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


def render_overview(df: pd.DataFrame) -> None:
    st.subheader("Consumption overview")
    render_key_insights(df)
    kpis = calculate_kpis(df)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Average Consumption", format_mw(kpis["avg_consumption"]))
    with col2:
        metric_card("Peak Consumption", format_mw(kpis["peak_consumption"]), "Highest daily value")
    with col3:
        metric_card("Minimum Consumption", format_mw(kpis["min_consumption"]), "Lowest daily value")
    with col4:
        metric_card("Latest Consumption", format_mw(kpis["latest_consumption"]), "Most recent observation")

    chart1, chart2 = st.columns(2)
    with chart1:
        st.plotly_chart(build_daily_trend(df), use_container_width=True)
    with chart2:
        st.plotly_chart(build_monthly_average_chart(df), use_container_width=True)

    st.plotly_chart(build_yearly_trend(df), use_container_width=True)
    st.plotly_chart(build_seasonality_heatmap(df), use_container_width=True)

    st.caption("Top 10 highest-consumption days")
    st.dataframe(build_top_days_table(df), use_container_width=True, hide_index=True)


def render_insights(df: pd.DataFrame) -> None:
    st.subheader("Consumption insights")
    insights = generate_insights(df)
    if not insights:
        st.info("No data is available for the selected range.")
        return

    for insight in insights:
        st.write(f"- {insight}")

    st.download_button(
        label="Download insight summary",
        data="\n".join(insights),
        file_name="up_electricity_insights.txt",
        mime="text/plain",
    )


def render_data_quality(df: pd.DataFrame, quality_report: dict) -> None:
    st.subheader("Data quality audit")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Rows after cleaning", f"{quality_report['row_count_after']:,}")
    with col2:
        metric_card("Duplicates removed", f"{quality_report['duplicate_count_before']:,}")
    with col3:
        metric_card("Date range", f"{quality_report['date_range']['start']} → {quality_report['date_range']['end']}")
    with col4:
        metric_card("Numeric issues", f"{sum(quality_report['invalid_numeric_rows'].values()):,}")

    st.write("### Cleaning steps")
    for step in quality_report["cleaning_steps"]:
        st.write(f"- {step}")


def render_empty_state() -> None:
    st.info("The selected date range returned no rows. Please broaden the filter window to continue exploring the data.")


def render_downloads(filtered_df: pd.DataFrame, cleaned_df: pd.DataFrame, summary_text: str) -> None:
    st.sidebar.markdown("### Downloads")
    st.sidebar.download_button(
        label="Download filtered data",
        data=filtered_df.to_csv(index=False),
        file_name="up_electricity_filtered.csv",
        mime="text/csv",
    )
    st.sidebar.download_button(
        label="Download cleaned data",
        data=cleaned_df.to_csv(index=False),
        file_name="up_electricity_cleaned.csv",
        mime="text/csv",
    )
    st.sidebar.download_button(
        label="Download insight summary",
        data=summary_text,
        file_name="up_electricity_summary.txt",
        mime="text/plain",
    )


def main() -> None:
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False

    st.sidebar.title("Uttar Pradesh Electricity Consumption Dashboard")
    st.sidebar.caption("Daily electricity consumption analytics for Uttar Pradesh")
    st.sidebar.markdown("---")
    st.sidebar.checkbox("Dark mode", key="dark_mode")

    uploaded_file = st.sidebar.file_uploader("Upload energy CSV", type=["csv"])

    try:
        df, quality_report = load_data(uploaded_file)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    filters = build_filters(df)
    filtered_df = apply_filters(df, filters)

    style_header(
        "Uttar Pradesh Electricity Consumption Dashboard",
        "Interactive electricity consumption analytics for Uttar Pradesh",
    )

    if filtered_df.empty:
        render_empty_state()
        return

    render_downloads(filtered_df, df, "\n".join(generate_insights(filtered_df)))

    page = st.sidebar.radio("Navigation", ["Overview", "Insights", "Data Quality"], index=0)
    if page == "Overview":
        render_overview(filtered_df)
    elif page == "Insights":
        render_insights(filtered_df)
    else:
        render_data_quality(filtered_df, quality_report)

    st.markdown(
        f"""
        <div style="margin-top: 1.2rem; padding: 0.9rem 1rem; border-top: 1px solid {THEME['border']}; color:{THEME['muted']}; font-size:0.9rem; line-height: 1.55;">
            <strong style="color:{THEME['text']};">Focus areas:</strong> Daily consumption monitoring, monthly averages, and yearly trend analysis<br>
            <strong style="color:{THEME['text']};">Key metrics:</strong> Average, peak, minimum, latest, and total electricity consumption in MW
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
