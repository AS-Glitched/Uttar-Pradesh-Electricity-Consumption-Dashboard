import json
import urllib.request
from urllib.error import URLError

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from src.config import (
    LOCAL_GEOJSON_PATH,
    INDIA_GEOJSON_SOURCES,
    GEOJSON_STATE_KEY_CANDIDATES,
    INDIA_STATE_GEO_NAMES,
    NON_GEOGRAPHIC_ENTITIES,
    REGION_COORDINATES,
)

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

def build_region_map(df: pd.DataFrame) -> tuple[go.Figure, pd.DataFrame]:
    """Build a full India choropleth map with interactive tooltips and zooming."""
    summary = (
        df.groupby(["region", "region_normalized"])["consumption_mw"]
        .sum()
        .reset_index()
        .sort_values("consumption_mw", ascending=False)
    )
    summary["geo_state"] = summary["region_normalized"].map(INDIA_STATE_GEO_NAMES)

    geographic = summary[~summary["region_normalized"].isin(NON_GEOGRAPHIC_ENTITIES)].copy()
    non_geo = summary[summary["region_normalized"].isin(NON_GEOGRAPHIC_ENTITIES)].copy()

    choropleth_data = (
        geographic.dropna(subset=["geo_state"])
        .groupby("geo_state", as_index=False)["consumption_mw"]
        .sum()
        .sort_values("consumption_mw", ascending=False)
        .reset_index(drop=True)
    )

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
        all_geo_states = [
            feat["properties"][geo_prop]
            for feat in geojson["features"]
            if geo_prop in feat.get("properties", {})
        ]
        full_states = pd.DataFrame({"geo_state": all_geo_states})
        merged = full_states.merge(choropleth_data, on="geo_state", how="left")

        hover_texts = []
        for _, row in merged.iterrows():
            if pd.isna(row["consumption_mw"]):
                hover_texts.append(
                    f"<b>{row['geo_state']}</b><br>"
                    f"<i>No data available</i>"
                )
            else:
                hover_texts.append(
                    f"<b>{row['geo_state']}</b><br>"
                    f"Consumption: {row['consumption_formatted']} MW<br>"
                    f"Rank: #{int(row['rank'])} of {len(choropleth_data)}<br>"
                    f"Share: {row['pct_of_total']}% of total"
                )
        merged["hover_text"] = hover_texts

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
                    tickformat="~s", # dynamic suffix formatting
                    outlinewidth=0,
                ),
                marker_line_width=0.7,
                marker_line_color="rgba(255,255,255,0.6)",
                text=merged["hover_text"],
                hovertemplate="%{text}<extra></extra>",
                zauto=True,
            )
        )

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
    else:
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
        dragmode="zoom", # Enables zooming explicitly
    )
    return fig, non_geo
