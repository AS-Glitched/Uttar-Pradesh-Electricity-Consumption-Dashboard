# Implementation Plan

1. File structure
- app.py: main Streamlit dashboard application
- data/sample_sales.csv: default sample dataset for portfolio demos
- requirements.txt: Python dependencies

2. Data processing steps
- Load CSV from uploader or fallback sample file
- Map flexible column names to expected fields
- Clean missing values, remove duplicates, parse dates, and standardize text
- Create KPI and trend columns such as profit margin and average selling price

3. UI sections
- Sidebar filters and navigation for Overview, Product Analysis, Regional Analysis, Trends, Data Quality, and Insights & Recommendations
- Header, KPI cards, charts, tables, and a footer for portfolio polish

4. Chart list
- Monthly sales and profit trends
- Sales and profit by category
- Segment share donut chart
- Top products by sales and profit
- Sales vs. profit scatter plot
- Regional performance bars and tables
- Quarterly and monthly growth trend visuals

5. Assumptions
- The input file is a retail-style CSV with sales and profit columns
- If exact column names differ, the app will map common variants gracefully
- The app prioritizes clarity and polish over excessive complexity
