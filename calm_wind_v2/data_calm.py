"""Téléchargement + nettoyage des séries de vent (ré-écrit à zéro, pas d'import
depuis src/). Bordeaux et Milan servent de proxy vent calme (moyennes 5.1 et
3.3 m/s, bien en dessous du site offshore vietnamien)."""
import requests
import pandas as pd
import numpy as np

SITES = {
    "bordeaux": (44.8378, -0.5792),
    "milan": (45.4642, 9.19),
}


def download(lat, lon, start_date="2015-01-01", end_date="2025-12-31"):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start_date, "end_date": end_date,
        "hourly": "wind_speed_100m,wind_speed_10m,wind_direction_100m,"
                  "temperature_2m,surface_pressure,precipitation",
        "wind_speed_unit": "ms",
        "timezone": "UTC",
    }
    r = requests.get(url, params=params, timeout=60)
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
    return df


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
        raise ValueError(f"Seulement {len(df)} lignes après nettoyage")
    return df.reset_index().rename(columns={"index": "time"})


def load_site(name, cache_dir):
    import os
    path = os.path.join(cache_dir, f"{name}_raw_v2.csv")
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["time"])
    else:
        lat, lon = SITES[name]
        df = clean(download(lat, lon))
        df.to_csv(path, index=False)
    return df
