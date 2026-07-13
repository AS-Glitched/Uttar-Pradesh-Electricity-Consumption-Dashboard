import pandas as pd
import streamlit as st
from datetime import timedelta

from src.config import (
    DEFAULT_DATA_PATH,
    FALLBACK_DATA_PATH,
    MONTH_ORDER,
    get_season,
    normalize_column_name,
)

@st.cache_data(show_spinner=False)
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
    available_seasons = sorted(df["season"].unique().tolist())
    available_regions = sorted(df["region"].unique().tolist())

    selected_years = st.sidebar.multiselect("Year", available_years, default=available_years)
    selected_months = st.sidebar.multiselect("Month", available_months, default=available_months)
    selected_seasons = st.sidebar.multiselect("Season", available_seasons, default=available_seasons)
    selected_regions = st.sidebar.multiselect("Region / State", available_regions, default=available_regions)
    view_by = st.sidebar.radio("Drill-down level", ["Daily", "Monthly", "Seasonal", "Custom"], index=0)

    return {
        "start_date": pd.Timestamp(start_date),
        "end_date": pd.Timestamp(end_date),
        "years": selected_years,
        "months": selected_months,
        "seasons": selected_seasons,
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
    if filters.get("seasons"):
        filtered = filtered[filtered["season"].isin(filters["seasons"])]
    if filters["regions"]:
        filtered = filtered[filtered["region"].isin(filters["regions"])]
    return filtered
