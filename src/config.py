import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = BASE_DIR / "data" / "Indias_Electricity_Consumption_.csv"
FALLBACK_DATA_PATH = BASE_DIR / "data" / "UP_electricity_consumption.csv"
LOCAL_GEOJSON_PATH = BASE_DIR / "data" / "india_states.geojson"

# Theme settings
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

# Date and Time constants
MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

SEASON_ORDER = ["Winter", "Spring", "Summer", "Autumn"]

def get_season(month_value: int) -> str:
    if month_value in {12, 1, 2}:
        return "Winter"
    if month_value in {3, 4, 5}:
        return "Spring"
    if month_value in {6, 7, 8}:
        return "Summer"
    return "Autumn"

# Geographic Constants
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
    "tamilnadu": {"lat": 11.1271, "lon": 78.6569},
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
    "NAME_1", "st_nm", "STATE_NAME", "NAME", "state_name", "STATE", "ST_NM",
]

# Maps normalized dataset column names → GeoJSON NAME_1 values.
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
    "tamilnadu": "Tamil Nadu", # FIXED from tamillnadu
    "telangana": "Telangana",
    "tripura": "Tripura",
    "up": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "westbengal": "West Bengal",
    "dd": "Dadra and Nagar Haveli and Daman and Diu",
    "dnh": "Dadra and Nagar Haveli and Daman and Diu",
}

NON_GEOGRAPHIC_ENTITIES = {"dvc", "essarsteel"}

def normalize_column_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())

def format_mw(value: float) -> str:
    return f"{value:,.2f} MW"
