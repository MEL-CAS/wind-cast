# ══ src/opendata.py — NOUVEAU FICHIER ══
# Géocodage + téléchargement + nettoyage, réutilisés depuis le notebook validé.
import requests
import pandas as pd
import numpy as np


def geocode_location(place_name):
    """Résout un nom de lieu en coordonnées GPS via l'API Geocoding d'Open-Meteo.
    Gratuite, sans clé, sans inscription. Renvoie None si rien n'est trouvé."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": place_name, "count": 5, "language": "fr"}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    if "results" not in data or len(data["results"]) == 0:
        return None
    return data["results"]  # liste de candidats, pas un seul — cf. page Import


def download_wind_dataset(lat, lon, start_date, end_date):
    """Télécharge les 6 variables nécessaires, format attendu par diagnose_and_clean()."""
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
        "ma_cible": d["wind_speed_100m"],
        "variable_secondaire": d["wind_speed_10m"],
        "direction": d["wind_direction_100m"],
        "temperature": d["temperature_2m"],
        "pression": d["surface_pressure"],
        "precipitation": d["precipitation"],
    })
    return df


def diagnose_and_clean(df, datetime_col, target_col, secondary_col, temperature_col,
                        pressure_col, precipitation_col, direction_col, min_rows=5000):
    """Version Streamlit-friendly : retourne (df_clean, fixes, warnings) au lieu
    de tout imprimer — la page Import se charge de l'affichage."""
    fixes, warnings = [], []
    df = df.copy()

    df[datetime_col] = pd.to_datetime(df[datetime_col], errors='coerce')
    n_bad = df[datetime_col].isna().sum()
    if n_bad > 0:
        df = df.dropna(subset=[datetime_col])
        fixes.append(f"{n_bad} lignes supprimées (datetime illisible)")

    n_dup = df[datetime_col].duplicated().sum()
    if n_dup > 0:
        df = df.drop_duplicates(subset=datetime_col, keep='first')
        fixes.append(f"{n_dup} doublons de timestamp supprimés")

    df = df.sort_values(datetime_col).set_index(datetime_col)
    median_gap = df.index.to_series().diff().median()
    full_range = pd.date_range(df.index.min(), df.index.max(), freq=median_gap)
    n_missing = len(full_range) - len(df)
    if n_missing > 0:
        df = df.reindex(full_range)
        fixes.append(f"{n_missing} pas de temps manquants réinsérés")

    numeric_cols = [target_col, secondary_col, temperature_col, pressure_col, precipitation_col, direction_col]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    if df[target_col].isna().sum() > 0:
        n_before = df[target_col].isna().sum()
        df[target_col] = df[target_col].interpolate(method='linear', limit=3, limit_direction='forward')
        n_after = df[target_col].isna().sum()
        if n_after > 0:
            df = df.dropna(subset=[target_col])
            fixes.append(f"Cible : {n_after} lignes supprimées (trou non interpolable)")
        if n_before - n_after > 0:
            fixes.append(f"Cible : {n_before - n_after} NaN comblés par interpolation")

    for col in [secondary_col, temperature_col, pressure_col, precipitation_col, direction_col]:
        pct_nan = df[col].isna().mean() * 100
        if pct_nan == 100:
            raise ValueError(f"Colonne '{col}' 100% NaN — indisponible pour ce site/cette période.")
        elif pct_nan > 0:
            df[col] = df[col].interpolate(method='linear', limit_direction='both')
            fixes.append(f"{col} : NaN comblés par interpolation ({pct_nan:.1f}%)")

    n_bad_dir = ((df[direction_col] < 0) | (df[direction_col] > 360)).sum()
    if n_bad_dir > 0:
        df[direction_col] = df[direction_col] % 360
        fixes.append(f"Direction : {n_bad_dir} valeurs recalées dans [0,360]")

    if df[temperature_col].max() > 60 or df[temperature_col].min() < -60:
        warnings.append("Température hors [-60, 60]°C — à vérifier")
    if df[pressure_col].max() > 1100 or df[pressure_col].min() < 850:
        warnings.append("Pression hors [850, 1100] hPa — à vérifier")

    if len(df) < min_rows:
        raise ValueError(f"Seulement {len(df):,} lignes après nettoyage — minimum {min_rows:,} requis.")

    return df.reset_index().rename(columns={'index': datetime_col}), fixes, warnings