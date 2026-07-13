# UrjaView: India Power Analytics

A sleek, interactive Streamlit dashboard for analyzing daily electricity consumption trends across Indian states and regions. UrjaView provides an intuitive interface for macro-level geographic insights and detailed micro-level temporal analysis.

## Core Features
- **Geographic Mapping**: A full interactive choropleth map of India plotting state-wise energy consumption with a beautifully contrasting Plasma color scale and rich hover tooltips. 
- **Time-Series Analysis**: Analyze long-term yearly trends, monthly averages, and daily fluctuations.
- **Seasonality Heatmap**: Detect power consumption intensity across different months and years.
- **Forecasting & Anomalies**: Built-in 30-day linear regression forecasting and z-score based anomaly detection for identifying unusual consumption spikes.
- **Drill-down Explorer**: Refine views by season, month, or custom date ranges to deeply understand granular trends.

## Tech Stack
- **Framework**: Streamlit
- **Data Manipulation**: Pandas, NumPy
- **Data Visualization**: Plotly Express, Plotly Graph Objects
- **Geospatial Mapping**: GeoJSON (Local bundle for offline capability)
- **Styling**: Vanilla CSS, Google Fonts (Inter)

## Running Locally
Ensure you have the required dependencies installed:
```bash
pip install -r requirements.txt
```

Run the dashboard:
```bash
streamlit run app.py
```

## Deployment
This app is ready to be deployed on Streamlit Community Cloud. Simply connect this repository to your Streamlit Cloud account and set the main file path to `app.py`.
