import pandas as pd
import numpy as np

def detect_frequency(df, datetime_col):
    dt = pd.to_datetime(df[datetime_col]).sort_values()
    median_gap = dt.diff().median()
    if median_gap <= pd.Timedelta(hours=1):  return "hourly"
    elif median_gap <= pd.Timedelta(days=1):  return "daily"
    elif median_gap <= pd.Timedelta(days=31): return "monthly"
    return "other"


def build_features(df, datetime_col, target_col, feature_cols,
                  lags=(1, 2, 3), rolling_windows=(6, 24), add_cyclic=True):
    df = df.copy()
    df[datetime_col] = pd.to_datetime(df[datetime_col])
    df = df.set_index(datetime_col).sort_index()
    freq = detect_frequency(df.reset_index(), datetime_col)
    all_features = list(feature_cols)

    for col in [target_col] + list(feature_cols):
        for lag in lags:
            name = f"{col}_lag{lag}"
            df[name] = df[col].shift(lag)
            all_features.append(name)

    for col in [target_col] + list(feature_cols):
        for w in rolling_windows:
            name = f"{col}_roll{w}"
            df[name] = df[col].shift(1).rolling(w).mean()  # shift AVANT rolling = causal
            all_features.append(name)

    if add_cyclic:
        if freq == "hourly":
            df["hour_sin"] = np.sin(2*np.pi*df.index.hour/24)
            df["hour_cos"] = np.cos(2*np.pi*df.index.hour/24)
            df["doy_sin"]  = np.sin(2*np.pi*df.index.dayofyear/365)
            df["doy_cos"]  = np.cos(2*np.pi*df.index.dayofyear/365)
            all_features += ["hour_sin", "hour_cos", "doy_sin", "doy_cos"]
        elif freq == "daily":
            df["dow_sin"]   = np.sin(2*np.pi*df.index.dayofweek/7)
            df["dow_cos"]   = np.cos(2*np.pi*df.index.dayofweek/7)
            df["month_sin"] = np.sin(2*np.pi*df.index.month/12)
            df["month_cos"] = np.cos(2*np.pi*df.index.month/12)
            all_features += ["dow_sin", "dow_cos", "month_sin", "month_cos"]

    df = df.dropna()
    return df, all_features, freq