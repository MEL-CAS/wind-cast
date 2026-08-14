import requests
import pandas as pd
import numpy as np
import torch

def fetch_live_wind(lat, lon, hours_needed):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "wind_speed_80m,wind_speed_120m,relative_humidity_2m,surface_pressure",
        "past_days": 2, "forecast_days": 1, "timezone": "UTC",
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    d = r.json()["hourly"]
    df = pd.DataFrame({
        "time": pd.to_datetime(d["time"]),
        "wind_speed_80m": d["wind_speed_80m"],
        "wind_speed_120m": d["wind_speed_120m"],
        "relative_humidity_2m": d["relative_humidity_2m"],
        "surface_pressure": d["surface_pressure"],
    })
    # Approximation 100m = moyenne 80m/120m — affichée comme telle dans l'UI
    df["wind_speed_100m_approx"] = 0.5*df["wind_speed_80m"] + 0.5*df["wind_speed_120m"]
    return df.dropna().tail(hours_needed).reset_index(drop=True)


def predict_next_hour(model, scaler_X, scaler_y, recent_df, features, window):
    X = scaler_X.transform(recent_df[features].tail(window)).astype(np.float32)
    X_tensor = torch.from_numpy(X).unsqueeze(0)
    model.eval()
    with torch.no_grad():
        pred_scaled = model(X_tensor).cpu().numpy()
    return float(scaler_y.inverse_transform(pred_scaled).flatten()[0])