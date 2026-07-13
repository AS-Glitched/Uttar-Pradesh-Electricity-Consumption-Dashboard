import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.config import THEME, MONTH_ORDER
from src.analytics import detect_anomalies

def apply_common_layout(fig: go.Figure, title: str, xaxis_title: str, yaxis_title: str):
    fig.update_layout(
        template="plotly_dark",
        title=title,
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        paper_bgcolor=THEME["bg"],
        plot_bgcolor=THEME["bg"],
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        font=dict(family="Inter, sans-serif"),
        hovermode="x unified",
        yaxis=dict(tickformat="~s"), # Human-readable scaling like 1k, 5k
    )
    return fig

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
            hovertemplate="%{y:,.2f} MW<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["rolling_avg_30d"],
            mode="lines",
            name="30-Day Avg",
            line=dict(color=THEME["secondary_accent"], width=2.6),
            hovertemplate="%{y:,.2f} MW<extra></extra>",
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
                hovertemplate="%{y:,.2f} MW (Anomaly)<extra></extra>",
            )
        )
        
    apply_common_layout(fig, "Daily Consumption Trend", "Date", "MW")
    return fig

def build_monthly_average_chart(df: pd.DataFrame) -> go.Figure:
    monthly = (
        df.groupby("month_name", observed=True)["consumption_mw"]
        .mean()
        .reset_index()
    )
    
    fig = px.bar(
        monthly,
        x="month_name",
        y="consumption_mw",
        text_auto=".2s",
        category_orders={"month_name": MONTH_ORDER}, # Fixes chronological ordering
        color_discrete_sequence=[THEME["secondary_accent"]],
    )
    
    apply_common_layout(fig, "Monthly Average Consumption", "Month", "Average MW")
    fig.update_traces(
        hovertemplate="%{x}<br>%{y:,.2f} MW<extra></extra>",
        textfont_size=10,
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
    apply_common_layout(fig, "Yearly Consumption Trend", "Year", "Total MW")
    fig.update_traces(hovertemplate="%{x}<br>%{y:,.2f} MW<extra></extra>")
    fig.update_xaxes(type="category") # Ensure years are distinct categories
    return fig

def build_seasonality_heatmap(df: pd.DataFrame) -> go.Figure:
    pivot = (
        df.assign(month_name=pd.Categorical(df["month_name"], categories=MONTH_ORDER, ordered=True))
        .pivot_table(index="year", columns="month_name", values="consumption_mw", aggfunc="mean")
        .reindex(columns=MONTH_ORDER)
    )
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
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        paper_bgcolor=THEME["bg"],
        plot_bgcolor=THEME["bg"],
        xaxis_title="Month",
        yaxis_title="Year",
        font=dict(family="Inter, sans-serif"),
    )
    fig.update_yaxes(type="category")
    return fig

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
            hovertemplate="%{y:,.2f} MW<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=forecast["date"],
            y=forecast["consumption_mw"],
            mode="lines",
            name="Forecast",
            line=dict(color="#60A5FA", width=2.2, dash="dash"),
            hovertemplate="%{y:,.2f} MW<extra></extra>",
        )
    )
    
    apply_common_layout(fig, f"{periods}-Day Forecast for Total Consumption", "Date", "MW")
    return fig
