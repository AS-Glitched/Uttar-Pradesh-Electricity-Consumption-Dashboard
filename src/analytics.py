import pandas as pd
import numpy as np

def calculate_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "avg_consumption": 0.0,
            "peak_consumption": 0.0,
            "min_consumption": 0.0,
            "latest_consumption": 0.0,
        }
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
    """Enhanced anomaly detection returning expected values and deviation amounts."""
    if df.empty or len(df) < window:
        return pd.DataFrame()

    # Assuming df is aggregated by date
    if "date" in df.columns:
        series = df.set_index("date")["consumption_mw"].sort_index()
    else:
        series = df["consumption_mw"].sort_index()

    rolling_mean = series.rolling(window=window, min_periods=3).mean()
    rolling_std = series.rolling(window=window, min_periods=3).std()
    
    # Calculate expected and deviations
    z_scores = (series - rolling_mean) / rolling_std
    deviations = series - rolling_mean
    deviation_pct = (deviations / rolling_mean) * 100

    anomalies_mask = z_scores.abs() > threshold
    anomalies = series[anomalies_mask].reset_index()

    if not anomalies.empty:
        anomalies["expected_value"] = rolling_mean.loc[anomalies["date"].values].values
        anomalies["deviation_mw"] = deviations.loc[anomalies["date"].values].values
        anomalies["deviation_pct"] = deviation_pct.loc[anomalies["date"].values].values
        anomalies["z_score"] = z_scores.loc[anomalies["date"].values].values
        
        # Add a short interpretation
        def interpret(row):
            if row["z_score"] > 0:
                if row["z_score"] > 4:
                    return "Severe Spike"
                return "Unusual Spike"
            else:
                if row["z_score"] < -4:
                    return "Severe Drop"
                return "Unusual Drop"
                
        anomalies["interpretation"] = anomalies.apply(interpret, axis=1)

    return anomalies

def build_top_days_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Date", "Consumption (MW)"])
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
    if df.empty:
        return pd.DataFrame(columns=["Region", "Total Consumption (MW)"])
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
    
    insights = []
    if len(monthly_avg) > 0:
        highest_month = monthly_avg.index[0]
        lowest_month = monthly_avg.index[-1]
        insights.append(f"{highest_month} is the most intensive month while {lowest_month} is the least intensive month on average.")

    insights.extend([
        f"Peak total consumption occurred on {peak_record.strftime('%b %d, %Y')}.",
        f"Lowest total consumption was observed on {min_record.strftime('%b %d, %Y')}.",
        f"{highest_region} has the highest cumulative consumption in the selected set.",
    ])

    daily_anomalies = detect_anomalies(df.groupby("date")["consumption_mw"].sum().reset_index())
    if not daily_anomalies.empty:
        spike_count = len(daily_anomalies[daily_anomalies['z_score'] > 0])
        drop_count = len(daily_anomalies[daily_anomalies['z_score'] < 0])
        insights.append(f"Detected {spike_count} unusual spikes and {drop_count} unusual drops in the selected period.")

    return insights
