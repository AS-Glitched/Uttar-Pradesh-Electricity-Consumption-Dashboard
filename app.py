import json
import re
import urllib.request
from datetime import timedelta
from pathlib import Path
from urllib.error import URLError

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "Indias_Electricity_Consumption_.csv"
FALLBACK_DATA_PATH = Path(__file__).resolve().parent / "data" / "UP_electricity_consumption.csv"
LOCAL_GEOJSON_PATH = Path(__file__).resolve().parent / "data" / "india_states.geojson"

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
SEASON_ORDER = ["Winter", "Spring", "Summer", "Autumn"]

REGION_COORDINATES = {
    "andhrapradesh": {"lat": 15.9129, "lon": 79.7400},
    "arunachalpradesh": {"lat": 28.2180, "lon": 94.7278},
    "assam": {"lat": 26.2006, "lon": 92.9376},
    "bihar": {"lat": 25.0961, "lon": 85.3131},
    "chandigarh": {"lat": 30.7333, "lon": 76.7794},
    "chhattisgarh": {"lat": 21.2951, "lon": 81.8282},
    "dd": {"lat": 20.4283, "lon": 72.8397},
    "delhi": {"lat": 28.7041, "lon": 77.1025},
    "dnh": {"lat": 20.1809, "lon": 73.0169},
    "dvc": {"lat": 23.6461, "lon": 86.1990},
    "essarsteel": {"lat": 21.2403, "lon": 81.6286},
    "goa": {"lat": 15.2993, "lon": 74.1240},
    "gujarat": {"lat": 22.2587, "lon": 71.1924},
    "haryana": {"lat": 29.0588, "lon": 76.0856},
    "hp": {"lat": 31.1048, "lon": 77.1734},
    "jk": {"lat": 33.7782, "lon": 76.5762},
    "jharkhand": {"lat": 23.6102, "lon": 85.2799},
    "karnataka": {"lat": 15.3173, "lon": 75.7139},
    "kerala": {"lat": 10.8505, "lon": 76.2711},
    "maharashtra": {"lat": 19.7515, "lon": 75.7139},
    "manipur": {"lat": 24.6637, "lon": 93.9063},
    "meghalaya": {"lat": 25.4670, "lon": 91.3662},
    "mizoram": {"lat": 23.1645, "lon": 92.9376},
    "mp": {"lat": 22.9734, "lon": 78.6569},
    "nagaland": {"lat": 26.1584, "lon": 94.5624},
    "odisha": {"lat": 20.9517, "lon": 85.0985},
    "pondy": {"lat": 11.9416, "lon": 79.8083},
    "punjab": {"lat": 31.1471, "lon": 75.3412},
    "rajasthan": {"lat": 27.0238, "lon": 74.2179},
    "sikkim": {"lat": 27.5330, "lon": 88.5122},
    "tamillnadu": {"lat": 11.1271, "lon": 78.6569},
    "telangana": {"lat": 18.1124, "lon": 79.0193},
    "tripura": {"lat": 23.9408, "lon": 91.9882},
    "up": {"lat": 26.8467, "lon": 80.9462},
    "uttarakhand": {"lat": 30.0668, "lon": 79.0193},
    "westbengal": {"lat": 22.9868, "lon": 87.8550},
}

INDIA_GEOJSON_SOURCES = [
    "https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson"
]
GEOJSON_STATE_KEY_CANDIDATES = [
    "NAME_1",
    "st_nm",
    "STATE_NAME",
    "NAME",
    "state_name",
    "STATE",
    "ST_NM",
]

# Maps normalized dataset column names → GeoJSON NAME_1 values.
# Note: GeoJSON uses older names "Orissa" and "Uttaranchal"; Telangana
# is merged into Andhra Pradesh in this GeoJSON vintage.
INDIA_STATE_GEO_NAMES = {
    "andhrapradesh": "Andhra Pradesh",
    "arunachalpradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chandigarh": "Chandigarh",
    "chhattisgarh": "Chhattisgarh",
    "delhi": "Delhi",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "hp": "Himachal Pradesh",
    "jk": "Jammu & Kashmir",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "maharashtra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "mp": "Madhya Pradesh",
    "nagaland": "Nagaland",
    "odisha": "Odisha",
    "pondy": "Puducherry",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamillnadu": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "up": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "westbengal": "West Bengal",
    "dd": "Dadra and Nagar Haveli and Daman and Diu",
    "dnh": "Dadra and Nagar Haveli and Daman and Diu",
}

# Entities in the dataset that are not geographic states/UTs.
NON_GEOGRAPHIC_ENTITIES = {"dvc", "essarsteel"}


@st.cache_data(show_spinner=False)
def load_india_geojson() -> dict | None:
    """Load India states GeoJSON — local file first, network fallback."""
    if LOCAL_GEOJSON_PATH.exists():
        try:
            with open(LOCAL_GEOJSON_PATH, encoding="utf-8") as fh:
                geojson = json.load(fh)
                if geojson.get("features"):
                    return geojson
        except (ValueError, OSError):
            pass
    for url in INDIA_GEOJSON_SOURCES:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                geojson = json.loads(response.read().decode("utf-8"))
                if geojson.get("features"):
                    return geojson
        except (URLError, ValueError, OSError):
            continue
    return None


def get_geojson_state_property(geojson: dict) -> str | None:
    first_feature = next(iter(geojson.get("features", [])), None)
    if not first_feature:
        return None
    properties = first_feature.get("properties", {})
    for key in GEOJSON_STATE_KEY_CANDIDATES:
        if key in properties:
            return key
    return next((key for key in properties if "name" in key.lower()), None)

st.set_page_config(page_title="UrjaView: India Power Analytics", page_icon="⚡", layout="wide")

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
    .stTabs [data-baseweb="tab-list"] {{ gap: 0.5rem; }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 999px;
        background: var(--card-bg);
        color: var(--muted);
        border: 1px solid var(--border);
        transition: all 0.2s ease;
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, var(--accent) 0%, #2563eb 100%);
        color: white;
        border-color: var(--accent);
    }}
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


def get_season(month_value: int) -> str:
    if month_value in {12, 1, 2}:
        return "Winter"
    if month_value in {3, 4, 5}:
        return "Spring"
    if month_value in {6, 7, 8}:
        return "Summer"
    return "Autumn"


def load_data(uploaded_file=None) -> tuple[pd.DataFrame, dict]:
    if uploaded_file is not None:
        raw = pd.read_csv(uploaded_file)
    elif DEFAULT_DATA_PATH.exists():
        raw = pd.read_csv(DEFAULT_DATA_PATH)
    elif FALLBACK_DATA_PATH.exists():
        raw = pd.read_csv(FALLBACK_DATA_PATH)
    else:
        raise ValueError("No energy dataset was found. Please upload a CSV file with energy data.")

    quality_report = {
        "source": "uploaded" if uploaded_file is not None else "sample",
        "row_count_before": len(raw),
        "duplicate_count_before": int(raw.duplicated().sum()),
        "missing_values_before": raw.isna().sum().to_dict(),
        "dtypes_before": {col: str(dtype) for col, dtype in raw.dtypes.items()},
        "invalid_numeric_rows": {},
        "cleaning_steps": [],
    }

    date_column = next((col for col in raw.columns if normalize_column_name(col) == "dates"), None)
    if not date_column:
        raise ValueError("The file must contain a Dates column.")

    total_column = next(
        (col for col in raw.columns if normalize_column_name(col) in {"totalconsumption", "total"}),
        None,
    )
    region_columns = [
        col
        for col in raw.columns
        if col != date_column and normalize_column_name(col) not in {"totalconsumption", "total"}
    ]
    if not region_columns:
        raise ValueError("The file must contain region/state consumption columns besides Dates.")

    raw = raw[[date_column] + region_columns + ([total_column] if total_column else [])].copy()
    raw[date_column] = pd.to_datetime(raw[date_column], errors="coerce")

    for col in region_columns:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")

    if total_column is not None:
        raw[total_column] = pd.to_numeric(raw[total_column], errors="coerce")
    else:
        raw["Total Consumption"] = raw[region_columns].sum(axis=1, min_count=1)
        total_column = "Total Consumption"

    quality_report["invalid_numeric_rows"] = raw[region_columns + [total_column]].isna().sum().to_dict()
    raw = raw.dropna(subset=[date_column]).reset_index(drop=True)

    melted = raw.melt(
        id_vars=[date_column],
        value_vars=region_columns,
        var_name="region",
        value_name="consumption_mw",
    )
    melted = melted.dropna(subset=["consumption_mw"]).reset_index(drop=True)
    melted["year"] = melted[date_column].dt.year
    melted["month"] = melted[date_column].dt.month
    melted["month_name"] = melted[date_column].dt.month_name()
    melted["season"] = melted[date_column].dt.month.apply(get_season)
    melted["day_name"] = melted[date_column].dt.day_name()
    melted["region_normalized"] = melted["region"].apply(normalize_column_name)
    melted.rename(columns={date_column: "date"}, inplace=True)

    invalid_negative = melted[melted["consumption_mw"] < 0]
    invalid_negative_count = len(invalid_negative)
    invalid_negative_dates = sorted(invalid_negative["date"].dt.strftime("%Y-%m-%d").unique().tolist())
    if invalid_negative_count > 0:
        melted = melted[melted["consumption_mw"] >= 0].reset_index(drop=True)
        quality_report["invalid_negative_count"] = invalid_negative_count
        quality_report["invalid_negative_dates"] = invalid_negative_dates
    else:
        quality_report["invalid_negative_count"] = 0
        quality_report["invalid_negative_dates"] = []

    quality_report["row_count_after"] = len(melted)
    quality_report["duplicate_count_after"] = int(melted.duplicated().sum())
    quality_report["missing_values_after"] = melted.isna().sum().to_dict()
    quality_report["date_range"] = {
        "start": melted["date"].min().strftime("%Y-%m-%d"),
        "end": melted["date"].max().strftime("%Y-%m-%d"),
    }
    quality_report["cleaning_steps"] = [
        "Loaded the Dates and region/state columns",
        "Converted the date column into datetime format",
        "Converted state consumption values to numeric format",
        "Created a long-form dataset for region-level analysis",
        "Added year, month, season, and normalized region fields",
    ]
    if invalid_negative_count > 0:
        quality_report["cleaning_steps"].append(
            f"Removed {invalid_negative_count} negative consumption readings from {len(invalid_negative_dates)} dates"
        )

    return melted, quality_report


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
    else:
        start_date = st.sidebar.date_input("Start date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.sidebar.date_input("End date", max_date, min_value=min_date, max_value=max_date)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    available_years = sorted(df["year"].unique().tolist())
    available_months = [m for m in MONTH_ORDER if m in df["month_name"].unique()]
    available_regions = sorted(df["region"].unique().tolist())

    selected_years = st.sidebar.multiselect("Year", available_years, default=available_years)
    selected_months = st.sidebar.multiselect("Month", available_months, default=available_months)
    selected_regions = st.sidebar.multiselect("Region / State", available_regions, default=available_regions)
    view_by = st.sidebar.radio("Drill-down level", ["Daily", "Monthly", "Seasonal", "Custom"], index=0)

    return {
        "start_date": pd.Timestamp(start_date),
        "end_date": pd.Timestamp(end_date),
        "years": selected_years,
        "months": selected_months,
        "regions": selected_regions,
        "view_by": view_by,
    }


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    filtered = df.copy()
    filtered = filtered[(filtered["date"] >= filters["start_date"]) & (filtered["date"] <= filters["end_date"])]
    if filters["years"]:
        filtered = filtered[filtered["year"].isin(filters["years"])]
    if filters["months"]:
        filtered = filtered[filtered["month_name"].isin(filters["months"])]
    if filters["regions"]:
        filtered = filtered[filtered["region"].isin(filters["regions"])]
    return filtered


def calculate_kpis(df: pd.DataFrame) -> dict:
    daily_totals = df.groupby("date")["consumption_mw"].sum()
    avg_consumption = float(daily_totals.mean())
    peak_consumption = float(daily_totals.max())
    min_consumption = float(daily_totals.min())
    latest_consumption = float(daily_totals.sort_index().iloc[-1])
    return {
        "avg_consumption": avg_consumption,
        "peak_consumption": peak_consumption,
        "min_consumption": min_consumption,
        "latest_consumption": latest_consumption,
    }


def detect_anomalies(df: pd.DataFrame, window: int = 14, threshold: float = 2.5) -> pd.DataFrame:
    series = df.set_index("date")["consumption_mw"].sort_index()
    rolling_mean = series.rolling(window=window, min_periods=3).mean()
    rolling_std = series.rolling(window=window, min_periods=3).std()
    z_scores = (series - rolling_mean) / rolling_std
    anomalies = series[(z_scores.abs() > threshold)].reset_index()
    if not anomalies.empty:
        anomalies["z_score"] = z_scores.loc[anomalies["date"].values].values
    return anomalies


def build_daily_trend(df: pd.DataFrame) -> go.Figure:
    daily = df.groupby("date")["consumption_mw"].sum().reset_index().sort_values("date")
    daily["rolling_avg_30d"] = daily["consumption_mw"].rolling(window=30, min_periods=5).mean()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["consumption_mw"],
            mode="lines+markers",
            name="Daily Consumption",
            line=dict(color=THEME["primary_accent"], width=1.4),
            marker=dict(size=4, color=THEME["primary_accent"]),
            hovertemplate="%{x|%b %d, %Y}<br>%{y:,.2f} MW<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["rolling_avg_30d"],
            mode="lines",
            name="30-Day Rolling Avg",
            line=dict(color=THEME["secondary_accent"], width=2.6),
            hovertemplate="%{x|%b %d, %Y}<br>%{y:,.2f} MW<extra></extra>",
        )
    )
    anomalies = detect_anomalies(daily)
    if not anomalies.empty:
        fig.add_trace(
            go.Scatter(
                x=anomalies["date"],
                y=anomalies["consumption_mw"],
                mode="markers",
                name="Anomaly",
                marker=dict(size=10, color="#F43F5E", symbol="x"),
                hovertemplate="%{x|%b %d, %Y}<br>%{y:,.2f} MW<br>Anomaly detected<extra></extra>",
            )
        )
    fig.update_layout(
        template="plotly_dark",
        title="Daily Consumption Trend",
        margin=dict(l=10, r=10, t=36, b=10),
        height=300,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        xaxis_title="Date",
        yaxis_title="MW",
        legend_title_text="",
        font=dict(family="Inter, sans-serif"),
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
        margin=dict(l=10, r=10, t=34, b=10),
        height=300,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        xaxis_title="Month",
        yaxis_title="Average MW",
        font=dict(family="Inter, sans-serif"),
    )
    fig.update_traces(
        hovertemplate="%{x}<br>%{y:,.2f} MW<extra></extra>",
        textfont_size=9,
    )
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
        margin=dict(l=10, r=10, t=34, b=10),
        height=300,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        xaxis_title="Year",
        yaxis_title="Total MW",
        font=dict(family="Inter, sans-serif"),
    )
    fig.update_traces(hovertemplate="%{x}<br>%{y:,.2f} MW<extra></extra>")
    return fig


def build_seasonality_heatmap(df: pd.DataFrame) -> go.Figure:
    pivot = (
        df.assign(month_name=pd.Categorical(df["month_name"], categories=MONTH_ORDER, ordered=True))
        .pivot_table(index="year", columns="month_name", values="consumption_mw", aggfunc="mean")
        .reindex(columns=MONTH_ORDER)
    )
    # Use NaN for missing data (shown as blank) instead of misleading zeros.
    z_values = pivot.values.tolist()
    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=list(pivot.columns),
            y=list(pivot.index),
            colorscale="Viridis",
            colorbar=dict(title="Average MW"),
            hoverongaps=False,
            hovertemplate="Year: %{y}<br>Month: %{x}<br>Avg: %{z:,.1f} MW<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        title="Seasonality: Month vs Year",
        margin=dict(l=10, r=10, t=34, b=10),
        height=300,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        xaxis_title="Month",
        yaxis_title="Year",
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def build_region_map(df: pd.DataFrame) -> go.Figure:
    """Build a full India choropleth map with UP emphasis."""
    # --- aggregate consumption by region ---
    summary = (
        df.groupby(["region", "region_normalized"])["consumption_mw"]
        .sum()
        .reset_index()
        .sort_values("consumption_mw", ascending=False)
    )
    summary["geo_state"] = summary["region_normalized"].map(INDIA_STATE_GEO_NAMES)

    # Filter out non-geographic entities (DVC, Essar Steel)
    geographic = summary[~summary["region_normalized"].isin(NON_GEOGRAPHIC_ENTITIES)].copy()
    non_geo = summary[summary["region_normalized"].isin(NON_GEOGRAPHIC_ENTITIES)].copy()

    # Aggregate regions mapped to the same GeoJSON state
    choropleth_data = (
        geographic.dropna(subset=["geo_state"])
        .groupby("geo_state", as_index=False)["consumption_mw"]
        .sum()
        .sort_values("consumption_mw", ascending=False)
        .reset_index(drop=True)
    )

    # Add rank and formatted values for tooltips
    choropleth_data["rank"] = range(1, len(choropleth_data) + 1)
    total_consumption = choropleth_data["consumption_mw"].sum()
    choropleth_data["pct_of_total"] = (
        (choropleth_data["consumption_mw"] / total_consumption * 100).round(1)
    )
    choropleth_data["consumption_formatted"] = (
        choropleth_data["consumption_mw"].apply(lambda v: f"{v:,.1f}")
    )

    geojson = load_india_geojson()
    geo_prop = get_geojson_state_property(geojson) if geojson else None

    if geojson and geo_prop and not choropleth_data.empty:
        # --- build all-India GeoJSON state list ---
        all_geo_states = [
            feat["properties"][geo_prop]
            for feat in geojson["features"]
            if geo_prop in feat.get("properties", {})
        ]
        # Create a dataframe for every GeoJSON state so all states render
        full_states = pd.DataFrame({"geo_state": all_geo_states})
        merged = full_states.merge(choropleth_data, on="geo_state", how="left")

        # Build the custom hover text
        hover_texts = []
        for _, row in merged.iterrows():
            if pd.isna(row["consumption_mw"]):
                hover_texts.append(
                    f"<b>{row['geo_state']}</b><br>"
                    f"<i>No consumption data available</i>"
                )
            else:
                hover_texts.append(
                    f"<b>{row['geo_state']}</b><br>"
                    f"Consumption: {row['consumption_formatted']} MW<br>"
                    f"Rank: #{int(row['rank'])} of {len(choropleth_data)}<br>"
                    f"Share: {row['pct_of_total']}% of total"
                )
        merged["hover_text"] = hover_texts

        # --- Base layer: draw all states in grey ---
        fig = go.Figure(
            go.Choropleth(
                geojson=geojson,
                locations=merged["geo_state"],
                z=[1] * len(merged),
                featureidkey=f"properties.{geo_prop}",
                colorscale=[[0, "#334155"], [1, "#334155"]],
                showscale=False,
                marker_line_width=0.7,
                marker_line_color="rgba(255,255,255,0.2)",
                text=merged["hover_text"],
                hovertemplate="%{text}<extra></extra>",
            )
        )

        # --- Main choropleth: data overlay, perceptually uniform scale ---
        fig.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=merged["geo_state"],
                z=merged["consumption_mw"],
                featureidkey=f"properties.{geo_prop}",
                colorscale="Plasma",
                colorbar=dict(
                    title=dict(text="Electricity<br>Consumption<br>(MW)", font=dict(size=11)),
                    thickness=14,
                    len=0.6,
                    yanchor="middle",
                    y=0.45,
                    tickfont=dict(size=10),
                    tickformat=",.0f",
                    outlinewidth=0,
                ),
                marker_line_width=0.7,
                marker_line_color="rgba(255,255,255,0.6)",
                text=merged["hover_text"],
                hovertemplate="%{text}<extra></extra>",
                zauto=True,
            )
        )

        # --- UP highlight: thick gold border ---
        up_feature = [
            feat for feat in geojson["features"]
            if feat.get("properties", {}).get(geo_prop) == "Uttar Pradesh"
        ]
        if up_feature:
            up_geojson = {"type": "FeatureCollection", "features": up_feature}
            up_row = merged[merged["geo_state"] == "Uttar Pradesh"]
            up_hover = up_row["hover_text"].values[0] if not up_row.empty else "Uttar Pradesh"
            fig.add_trace(
                go.Choropleth(
                    geojson=up_geojson,
                    locations=["Uttar Pradesh"],
                    z=[up_row["consumption_mw"].values[0] if not up_row.empty else 0],
                    featureidkey=f"properties.{geo_prop}",
                    colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                    marker_line_width=3,
                    marker_line_color="#FFD700",
                    showscale=False,
                    text=[f"<b>★ FOCUS STATE</b><br>{up_hover}"],
                    hovertemplate="%{text}<extra></extra>",
                )
            )

        # Map projection configurations
        fig.update_geos(
            fitbounds="locations",
            visible=False,
            bgcolor="#0F172A",
            projection_type="mercator",
            scope="asia",
            center=dict(lat=22.5, lon=80.0),
            lataxis_range=[6, 38],
            lonaxis_range=[68, 98],
        )

        # Annotation star and text for UP (using scattergeo to respect projection bounds)
        fig.add_trace(
            go.Scattergeo(
                lat=[26.8],
                lon=[80.9],
                mode="markers+text",
                marker=dict(size=14, color="#FFD700", symbol="star"),
                text=["<b>Uttar Pradesh</b><br><i>Focus State</i>"],
                textfont=dict(color="#FFD700", size=11, family="Inter, sans-serif"),
                textposition="top right",
                showlegend=False,
                hoverinfo="skip"
            )
        )

    else:
        # Fallback: scatter-geo if no GeoJSON available
        mapped = summary.copy()
        mapped["lat"] = mapped["region_normalized"].map(
            lambda v: REGION_COORDINATES.get(v, {}).get("lat")
        )
        mapped["lon"] = mapped["region_normalized"].map(
            lambda v: REGION_COORDINATES.get(v, {}).get("lon")
        )
        mapped = mapped.dropna(subset=["lat", "lon"])
        fig = px.scatter_geo(
            mapped,
            lat="lat",
            lon="lon",
            hover_name="region",
            size="consumption_mw",
            color="consumption_mw",
            color_continuous_scale="Plasma",
            projection="mercator",
            scope="asia",
            size_max=40,
            title="State/Region Consumption Map",
        )
        fig.update_geos(
            landcolor="#0F172A",
            oceancolor="#020617",
            lakecolor="#020617",
            showland=True,
            showcountries=True,
            showcoastlines=False,
            lataxis_range=[6, 38],
            lonaxis_range=[68, 98],
            center=dict(lat=22.5, lon=80.0),
        )
        fig.update_traces(
            marker=dict(opacity=0.85, line=dict(width=0.8, color="#FFFFFF")),
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "Consumption: %{marker.color:,.1f} MW<extra></extra>"
            ),
        )

    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text="India — State-wise Electricity Consumption",
            font=dict(size=16, family="Inter, sans-serif"),
            x=0.5,
            xanchor="center",
        ),
        margin=dict(l=8, r=8, t=50, b=8),
        height=540,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        font=dict(family="Inter, sans-serif"),
    )
    return fig, non_geo

def build_forecast_chart(df: pd.DataFrame, periods: int = 30) -> go.Figure:
    daily = df.groupby("date")["consumption_mw"].sum().reset_index().sort_values("date")
    if len(daily) < 6:
        return build_daily_trend(df)

    x = np.arange(len(daily))
    y = daily["consumption_mw"].to_numpy()
    coeffs = np.polyfit(x, y, 1)
    trend = np.poly1d(coeffs)
    forecast_index = np.arange(len(daily), len(daily) + periods)
    forecast_values = trend(forecast_index)

    forecast_dates = pd.date_range(start=daily["date"].iloc[-1] + pd.Timedelta(days=1), periods=periods)
    forecast = pd.DataFrame({"date": forecast_dates, "consumption_mw": forecast_values})

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["consumption_mw"],
            mode="lines",
            name="Actual",
            line=dict(color=THEME["primary_accent"], width=2.2),
            hovertemplate="%{x|%b %d, %Y}<br>%{y:,.2f} MW<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast["date"],
            y=forecast["consumption_mw"],
            mode="lines",
            name="Forecast",
            line=dict(color="#60A5FA", width=2.2, dash="dash"),
            hovertemplate="%{x|%b %d, %Y}<br>%{y:,.2f} MW<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        title=f"{periods}-Day Forecast for Total Consumption",
        margin=dict(l=10, r=10, t=34, b=10),
        height=300,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        xaxis_title="Date",
        yaxis_title="MW",
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def build_top_days_table(df: pd.DataFrame) -> pd.DataFrame:
    top_days = (
        df.groupby("date")["consumption_mw"]
        .sum()
        .reset_index()
        .sort_values("consumption_mw", ascending=False)
        .head(10)
    )
    top_days["date"] = top_days["date"].dt.strftime("%Y-%m-%d")
    top_days["consumption_mw"] = top_days["consumption_mw"].round(2)
    top_days.columns = ["Date", "Consumption (MW)"]
    return top_days


def build_top_regions_table(df: pd.DataFrame) -> pd.DataFrame:
    top_regions = (
        df.groupby("region")["consumption_mw"]
        .sum()
        .reset_index()
        .sort_values("consumption_mw", ascending=False)
        .head(12)
    )
    top_regions["consumption_mw"] = top_regions["consumption_mw"].round(2)
    top_regions.columns = ["Region", "Total Consumption (MW)"]
    return top_regions


def generate_insights(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []

    daily_totals = df.groupby("date")["consumption_mw"].sum()
    peak_record = daily_totals.idxmax()
    min_record = daily_totals.idxmin()
    highest_region = df.groupby("region")["consumption_mw"].sum().idxmax()
    monthly_avg = df.groupby("month_name")["consumption_mw"].mean().sort_values(ascending=False)
    highest_month = monthly_avg.index[0]
    lowest_month = monthly_avg.index[-1]

    insights = [
        f"Peak total consumption occurred on {peak_record.strftime('%b %d, %Y')}.",
        f"Lowest total consumption was observed on {min_record.strftime('%b %d, %Y')}.",
        f"{highest_region} has the highest cumulative consumption in the selected set.",
        f"{highest_month} is the most intensive month while {lowest_month} is the least intensive month on average.",
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


def _render_non_geo_note(non_geo: pd.DataFrame) -> None:
    """Show a small note about non-geographic entities excluded from the map."""
    if non_geo.empty:
        return
    items = ", ".join(
        f"{row['region']} ({row['consumption_mw']:,.1f} MW)"
        for _, row in non_geo.iterrows()
    )
    st.caption(
        f"ℹ️ Non-geographic entities excluded from map: {items}"
    )


def render_overview(df: pd.DataFrame) -> None:
    st.subheader("Consumption overview")
    render_key_insights(df)
    kpis = calculate_kpis(df)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Average Daily Consumption", format_mw(kpis["avg_consumption"]))
    with col2:
        metric_card("Peak Daily Consumption", format_mw(kpis["peak_consumption"]), "Highest total day")
    with col3:
        metric_card("Minimum Daily Consumption", format_mw(kpis["min_consumption"]), "Lowest total day")
    with col4:
        metric_card("Latest Daily Consumption", format_mw(kpis["latest_consumption"]), "Most recent day")

    st.plotly_chart(build_daily_trend(df), width="stretch")
    chart1, chart2 = st.columns(2)
    with chart1:
        st.plotly_chart(build_monthly_average_chart(df), width="stretch")
    with chart2:
        st.plotly_chart(build_yearly_trend(df), width="stretch")

    map_fig, non_geo = build_region_map(df)
    st.plotly_chart(map_fig, width="stretch")
    _render_non_geo_note(non_geo)
    st.caption("Top regions by cumulative consumption")
    st.dataframe(build_top_regions_table(df), width="stretch", hide_index=True)


def render_drill_down(df: pd.DataFrame, filters: dict) -> None:
    st.subheader("Drill-down explorer")
    st.write("Refine the view by month, season, or a custom date range using the sidebar filters.")

    if df.empty:
        st.info("No data is available for the selected filters.")
        return

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
        metric_card("Latest", format_mw(kpis["latest_consumption"]))

        with st.expander("Anomaly detection"):
            daily = df.groupby("date")["consumption_mw"].sum().reset_index().sort_values("date")
            anomalies = detect_anomalies(daily)
            if anomalies.empty:
                st.info("No significant consumption spikes detected in this range.")
            else:
                st.write("Anomalous consumption dates:")
                anomalies_display = anomalies.copy()
                anomalies_display["date"] = anomalies_display["date"].dt.strftime("%Y-%m-%d")
                anomalies_display["consumption_mw"] = anomalies_display["consumption_mw"].round(2)
                anomalies_display["z_score"] = anomalies_display["z_score"].round(2)
                st.dataframe(
                    anomalies_display.rename(
                        columns={"consumption_mw": "Consumption (MW)", "z_score": "Z-Score"}
                    ),
                    hide_index=True,
                    width="stretch",
                )

    st.markdown("---")
    bottom_col1, bottom_col2 = st.columns(2)
    with bottom_col1:
        st.caption("Top regions by consumption")
        st.dataframe(build_top_regions_table(df), width="stretch", hide_index=True)
    with bottom_col2:
        st.caption("Top consumption days")
        st.dataframe(build_top_days_table(df), width="stretch", hide_index=True)


def render_map_forecast(df: pd.DataFrame) -> None:
    st.subheader("Map, forecasting, and anomalies")
    st.write("Visualize the geographic distribution across states and forecast future totals for the selected range.")

    map_fig, non_geo = build_region_map(df)
    st.plotly_chart(map_fig, width="stretch")
    _render_non_geo_note(non_geo)
    st.plotly_chart(build_forecast_chart(df, periods=30), width="stretch")

    daily = df.groupby("date")["consumption_mw"].sum().reset_index().sort_values("date")
    anomalies = detect_anomalies(daily)
    if anomalies.empty:
        st.success("No major spike anomalies were detected for the selected period.")
    else:
        st.warning(f"Detected {len(anomalies)} anomalous consumption spikes in the selected range.")
        st.dataframe(
            anomalies.assign(date=anomalies["date"].dt.strftime("%Y-%m-%d"), consumption_mw=anomalies["consumption_mw"].round(2), z_score=anomalies["z_score"].round(2))
            .rename(columns={"consumption_mw": "Consumption (MW)", "z_score": "Z-Score"}),
            hide_index=True,
        )


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
        file_name="india_electricity_insights.txt",
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
        metric_card(
            "Invalid negative values",
            f"{quality_report.get('invalid_negative_count', 0):,}",
        )

    st.write("### Cleaning steps")
    for step in quality_report["cleaning_steps"]:
        st.write(f"- {step}")

    if quality_report.get("invalid_negative_count", 0) > 0:
        st.info(
            "Negative consumption readings were removed because they are invalid for this energy dataset. "
            "Review the data quality section for the count and affected dates."
        )


def render_empty_state() -> None:
    st.info("The selected date range returned no rows. Please broaden the filter window to continue exploring the data.")


def render_downloads(filtered_df: pd.DataFrame, cleaned_df: pd.DataFrame, summary_text: str) -> None:
    st.sidebar.markdown("### Downloads")
    st.sidebar.download_button(
        label="Download filtered data",
        data=filtered_df.to_csv(index=False),
        file_name="india_electricity_filtered.csv",
        mime="text/csv",
    )
    st.sidebar.download_button(
        label="Download cleaned data",
        data=cleaned_df.to_csv(index=False),
        file_name="india_electricity_cleaned.csv",
        mime="text/csv",
    )
    st.sidebar.download_button(
        label="Download insight summary",
        data=summary_text,
        file_name="india_electricity_summary.txt",
        mime="text/plain",
    )


def main() -> None:
    st.sidebar.title("UrjaView: India Power Analytics")
    st.sidebar.caption("Interactive electricity consumption analytics for India")
    st.sidebar.markdown("---")

    uploaded_file = st.sidebar.file_uploader("Upload energy CSV", type=["csv"])

    try:
        df, quality_report = load_data(uploaded_file)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    filters = build_filters(df)
    filtered_df = apply_filters(df, filters)

    style_header(
        "India Electricity Consumption Dashboard",
        "Interactive electricity consumption analytics for India",
    )

    if filtered_df.empty:
        render_empty_state()
        return

    render_downloads(filtered_df, df, "\n".join(generate_insights(filtered_df)))

    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Map & Forecast", "Drill-down", "Insights", "Data Quality"],
        index=0,
    )
    if page == "Overview":
        render_overview(filtered_df)
    elif page == "Map & Forecast":
        render_map_forecast(filtered_df)
    elif page == "Drill-down":
        render_drill_down(filtered_df, filters)
    elif page == "Insights":
        render_insights(filtered_df)
    else:
        render_data_quality(filtered_df, quality_report)

    st.markdown(
        f"""
        <div style="margin-top: 1.2rem; padding: 0.9rem 1rem; border-top: 1px solid {THEME['border']}; color:{THEME['muted']}; font-size:0.9rem; line-height: 1.55;">
            <strong style="color:{THEME['text']};">Focus areas:</strong> Geographic state-level consumption, trend forecasting, anomaly detection, and seasonal drill-downs.<br>
            <strong style="color:{THEME['text']};">Key metrics:</strong> Average, peak, minimum, latest, and total electricity consumption in MW.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
