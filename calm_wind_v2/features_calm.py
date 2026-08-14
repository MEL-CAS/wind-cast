"""Feature engineering ré-écrit à zéro. Ajoute des features pensées pour le
régime calme : volatilité récente (écart-type glissant) et tendance (delta),
en plus des lags/rolling/cycliques classiques."""
import numpy as np
import pandas as pd

TARGET = "wind_speed"


def build_features(df, lags=(1, 2, 3, 6), rolling_windows=(3, 6, 12, 24)):
    df = df.copy().set_index("time").sort_index()
    base_cols = ["wind_speed", "wind_speed_10m", "direction", "temperature", "pressure", "precipitation"]
    feats = []

    for col in base_cols:
        for lag in lags:
            name = f"{col}_lag{lag}"
            df[name] = df[col].shift(lag)
            feats.append(name)

    for col in ["wind_speed", "wind_speed_10m"]:
        for w in rolling_windows:
            m = f"{col}_roll{w}_mean"
            s = f"{col}_roll{w}_std"
            df[m] = df[col].shift(1).rolling(w).mean()
            df[s] = df[col].shift(1).rolling(w).std()
            feats += [m, s]

    # tendance courte (calme = souvent des plateaux, utile de détecter une rupture)
    df["wind_speed_delta1"] = df["wind_speed"].shift(1) - df["wind_speed"].shift(2)
    feats.append("wind_speed_delta1")

    df["hour_sin"] = np.sin(2 * np.pi * df.index.hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df.index.hour / 24)
    df["doy_sin"] = np.sin(2 * np.pi * df.index.dayofyear / 365)
    df["doy_cos"] = np.cos(2 * np.pi * df.index.dayofyear / 365)
    feats += ["hour_sin", "hour_cos", "doy_sin", "doy_cos"]

    df = df.dropna()
    return df, feats
