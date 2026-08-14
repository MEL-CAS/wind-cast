"""Data download/cache for the two validated sites (Milan = calm regime,
Wellington = strong regime). Download/clean logic ported verbatim from
calm_wind_v2/data_calm.py (same Open-Meteo archive endpoint/params) so the
calm-site data is byte-identical to what the existing xgb_calm_milan
research artifact was built from."""
import os
import requests
import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

SITES = {
    "milan": (45.4642, 9.19),
    "wellington": (-41.2865, 174.7762),
}

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARS = (
    "wind_speed_100m,wind_speed_10m,wind_direction_100m,"
    "temperature_2m,surface_pressure,precipitation"
)


def download(lat, lon, start_date="2015-01-01", end_date="2025-12-31"):
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start_date, "end_date": end_date,
        "hourly": HOURLY_VARS,
        "wind_speed_unit": "ms",
        "timezone": "UTC",
    }
    r = requests.get(ARCHIVE_URL, params=params, timeout=60)
    r.raise_for_status()
    d = r.json()["hourly"]
    return pd.DataFrame({
        "time": pd.to_datetime(d["time"]),
        "wind_speed": d["wind_speed_100m"],
        "wind_speed_10m": d["wind_speed_10m"],
        "direction": d["wind_direction_100m"],
        "temperature": d["temperature_2m"],
        "pressure": d["surface_pressure"],
        "precipitation": d["precipitation"],
    })


def clean(df, min_rows=5000):
    df = df.copy().sort_values("time").drop_duplicates(subset="time")
    df = df.set_index("time")
    full_range = pd.date_range(df.index.min(), df.index.max(), freq="h")
    df = df.reindex(full_range)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["wind_speed"] = df["wind_speed"].interpolate("linear", limit=3)
    for col in ["wind_speed_10m", "direction", "temperature", "pressure", "precipitation"]:
        df[col] = df[col].interpolate("linear", limit_direction="both")
    df = df.dropna()
    df["direction"] = df["direction"] % 360
    if len(df) < min_rows:
        raise ValueError(f"Only {len(df)} rows after cleaning")
    return df.reset_index().rename(columns={"index": "time"})


def load_site(name, cache_dir=CACHE_DIR):
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"{name}_raw.csv")
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=["time"])
    if name in ("milan", "bordeaux"):
        # reuse the already-downloaded calm_wind_v2 cache, no need to re-hit the API
        existing = os.path.join(os.path.dirname(__file__), "..", "calm_wind_v2", f"{name}_raw_v2.csv")
        if os.path.exists(existing):
            df = pd.read_csv(existing, parse_dates=["time"])
            df.to_csv(path, index=False)
            return df
    lat, lon = SITES[name]
    df = clean(download(lat, lon))
    df.to_csv(path, index=False)
    return df
