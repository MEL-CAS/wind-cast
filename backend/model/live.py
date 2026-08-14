"""Live data fetch for inference. Deliberately requests the SAME hourly
variables as the archive/training endpoint (wind_speed_100m directly, not an
80m/120m approximation like the old src/live.py) — Open-Meteo's forecast API
supports the identical variable names, so there is no reason for live and
historical feature schemas to diverge. This is a fix to how the data feed is
plumbed, not a change to any trained model behavior."""
import requests
import pandas as pd
import numpy as np

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = (
    "wind_speed_100m,wind_speed_10m,wind_direction_100m,"
    "temperature_2m,surface_pressure,precipitation"
)


def fetch_live_series(lat, lon, past_days=3, forecast_days=2):
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": HOURLY_VARS,
        "wind_speed_unit": "ms",
        "past_days": past_days, "forecast_days": forecast_days,
        "timezone": "UTC",
    }
    r = requests.get(FORECAST_URL, params=params, timeout=20)
    r.raise_for_status()
    d = r.json()["hourly"]
    df = pd.DataFrame({
        "time": pd.to_datetime(d["time"]),
        "wind_speed": d["wind_speed_100m"],
        "wind_speed_10m": d["wind_speed_10m"],
        "direction": d["wind_direction_100m"],
        "temperature": d["temperature_2m"],
        "pressure": d["surface_pressure"],
        "precipitation": d["precipitation"],
    })
    df = df.sort_values("time").drop_duplicates(subset="time").reset_index(drop=True)
    for col in df.columns:
        if col != "time":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.interpolate(limit_direction="both")
    df["direction"] = df["direction"] % 360
    return df.dropna()
