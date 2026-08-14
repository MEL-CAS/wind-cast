"""Strong-regime feature engineering — ported verbatim from
src/preprocessing.build_features (lags + causal rolling mean + cyclic
hour/day), specialized to the fixed 6-column wind schema. Hourly frequency
only (both validated sites are hourly), so detect_frequency's other branches
are dropped rather than ported unused."""
import numpy as np

TARGET = "wind_speed"
BASE_FEATURE_COLS = ["wind_speed_10m", "direction", "temperature", "pressure", "precipitation"]


def build_features(df, lags=(1, 2, 3), rolling_windows=(6, 24)):
    df = df.copy()
    df["time"] = df["time"] if np.issubdtype(df["time"].dtype, np.datetime64) else df["time"].astype("datetime64[ns]")
    df = df.set_index("time").sort_index()
    all_features = list(BASE_FEATURE_COLS)

    for col in [TARGET] + BASE_FEATURE_COLS:
        for lag in lags:
            name = f"{col}_lag{lag}"
            df[name] = df[col].shift(lag)
            all_features.append(name)

    for col in [TARGET] + BASE_FEATURE_COLS:
        for w in rolling_windows:
            name = f"{col}_roll{w}"
            df[name] = df[col].shift(1).rolling(w).mean()
            all_features.append(name)

    df["hour_sin"] = np.sin(2 * np.pi * df.index.hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df.index.hour / 24)
    df["doy_sin"] = np.sin(2 * np.pi * df.index.dayofyear / 365)
    df["doy_cos"] = np.cos(2 * np.pi * df.index.dayofyear / 365)
    all_features += ["hour_sin", "hour_cos", "doy_sin", "doy_cos"]

    df = df.dropna()
    return df, all_features
