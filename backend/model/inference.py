"""Single entry point: given (lat, lon), fetch live Open-Meteo data, build
features with the same pipelines used in training, route each of the next 24
hours to the calm (Milan-trained XGBoost) or strong (Wellington-trained
GRU+XGBoost-residual) model via the hysteresis regime state machine, and
return the full §2 API-contract forecast object."""
import os
import json
import numpy as np
import pandas as pd
import torch
import joblib
import xgboost as xgb

from model.live import fetch_live_series
from model.features_calm import build_features as build_features_calm
from model.features_strong import build_features as build_features_strong
from model.gru import GRUModel
from model import regime as regime_mod
from model.confidence import compute_confidence

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "weights")

_bundle_cache = {}


def _load_calm_bundle():
    if "calm" not in _bundle_cache:
        meta = joblib.load(os.path.join(WEIGHTS_DIR, "calm_milan_meta.pkl"))
        model = xgb.XGBRegressor()
        model.load_model(os.path.join(WEIGHTS_DIR, "xgb_calm_milan.json"))
        with open(os.path.join(WEIGHTS_DIR, "calm_milan_metrics.json")) as f:
            metrics = json.load(f)["test_metrics"]
        _bundle_cache["calm"] = {"model": model, **meta, "metrics": metrics}
    return _bundle_cache["calm"]


def _load_strong_bundle():
    if "strong" not in _bundle_cache:
        meta = joblib.load(os.path.join(WEIGHTS_DIR, "strong_wellington_meta.pkl"))
        gru = GRUModel(len(meta["features"]), **meta["gru_params"])
        gru.load_state_dict(torch.load(os.path.join(WEIGHTS_DIR, "gru_wellington.pt"), map_location="cpu"))
        gru.eval()
        xgb_res = xgb.XGBRegressor()
        xgb_res.load_model(os.path.join(WEIGHTS_DIR, "xgb_residual_wellington.json"))
        with open(os.path.join(WEIGHTS_DIR, "strong_wellington_metrics.json")) as f:
            metrics = json.load(f)["metrics_combined"]
        _bundle_cache["strong"] = {"gru": gru, "xgb_residual": xgb_res, **meta, "metrics": metrics}
    return _bundle_cache["strong"]


def _predict_calm_at(df_feat, pos, bundle):
    row = df_feat.iloc[[pos]][bundle["features"]]
    Xs = bundle["scaler_X"].transform(row).astype(np.float32)
    pred_s = bundle["model"].predict(Xs)
    return float(bundle["scaler_y"].inverse_transform(pred_s.reshape(-1, 1)).flatten()[0])


def _gru_pred_at(scaled_X, pos, W, bundle):
    """GRU prediction (real m/s) for row `pos`, using the W rows immediately
    preceding it (scaled_X[pos-W:pos])."""
    window = scaled_X[pos - W:pos]
    x = torch.from_numpy(window.astype(np.float32)).unsqueeze(0)
    with torch.no_grad():
        pred_scaled = bundle["gru"](x).numpy()
    return float(bundle["scaler_y"].inverse_transform(pred_scaled).flatten()[0])


def _predict_strong_at(df_feat, scaled_X, pos, bundle, gru_cache):
    W = bundle["window"]
    if pos not in gru_cache:
        gru_cache[pos] = _gru_pred_at(scaled_X, pos, W, bundle)
    if (pos - 1) not in gru_cache:
        gru_cache[pos - 1] = _gru_pred_at(scaled_X, pos - 1, W, bundle)
    pred_t, pred_tm1 = gru_cache[pos], gru_cache[pos - 1]
    grad = pred_t - pred_tm1
    raw_row = scaled_X[pos - 1]
    xgb_row = np.concatenate([raw_row, [pred_t, grad]]).reshape(1, -1)
    correction = float(bundle["xgb_residual"].predict(xgb_row)[0])
    return pred_t + correction


def forecast_24h(lat, lon, location_name=None):
    raw = fetch_live_series(lat, lon)
    now = pd.Timestamp.now(tz="UTC").tz_convert(None).floor("h")

    calm_bundle = _load_calm_bundle()
    strong_bundle = _load_strong_bundle()

    df_calm, feats_calm = build_features_calm(raw)
    df_strong, feats_strong = build_features_strong(raw)
    scaled_strong = strong_bundle["scaler_X"].transform(df_strong[strong_bundle["features"]]).astype(np.float32)

    target_times = [now + pd.Timedelta(hours=h) for h in range(1, 25)]
    available = [t for t in target_times if t in df_calm.index and t in df_strong.index]
    if len(available) < 24:
        raise ValueError(
            f"Only {len(available)} of 24 forecast hours have enough lookback data "
            "(Open-Meteo forecast horizon or feature window insufficient)."
        )

    # First pass: cheap regime pre-classification straight off Open-Meteo's own
    # forecast wind_speed_100m (persistence-style), then stabilize with hysteresis.
    raw_speed_by_time = raw.set_index("time")["wind_speed"]
    prelim = [float(raw_speed_by_time.get(t, raw_speed_by_time.iloc[-1])) for t in available]
    regimes = regime_mod.classify_hourly(prelim)

    gru_cache = {}
    forecast_points = []
    for t, reg in zip(available, regimes):
        if reg == "calm":
            pos = df_calm.index.get_loc(t)
            value = _predict_calm_at(df_calm, pos, calm_bundle)
        else:
            pos = df_strong.index.get_loc(t)
            value = _predict_strong_at(df_strong, scaled_strong, pos, strong_bundle, gru_cache)
        value = max(0.0, value)
        forecast_points.append({"time": t.isoformat() + "Z", "wind_speed": round(value, 2), "regime": reg})

    model_used = regime_mod.summarize_dual_usage(regimes)

    recent = raw[raw["time"] <= now].tail(48)["wind_speed"]
    recent_mean = float(recent.mean()) if len(recent) else float(raw["wind_speed"].mean())
    recent_std = float(recent.std()) if len(recent) > 1 else float(raw["wind_speed"].std())
    dominant_regime = "strong" if regimes.count("strong") >= regimes.count("calm") else "calm"
    base_accuracy = {
        "calm": calm_bundle["metrics"]["r2"],
        "strong": strong_bundle["metrics"]["r2"],
    }
    confidence = compute_confidence(dominant_regime, recent_mean, recent_std, regimes, base_accuracy=base_accuracy)

    metrics_used = calm_bundle["metrics"] if dominant_regime == "calm" else strong_bundle["metrics"]

    return {
        "location": {"name": location_name or f"{lat:.3f}, {lon:.3f}", "lat": lat, "lon": lon},
        "forecast_24h": [
            {"time": p["time"], "wind_speed": p["wind_speed"], "ci_low": round(max(0.0, p["wind_speed"] - metrics_used["mae"]), 2),
             "ci_high": round(p["wind_speed"] + metrics_used["mae"], 2)}
            for p in forecast_points
        ],
        "regime_by_hour": [{"time": p["time"], "regime": p["regime"]} for p in forecast_points],
        "model_used": model_used,
        "confidence": confidence,
        "metrics": {
            "mae": metrics_used["mae"], "rmse": metrics_used["rmse"],
            "mape": metrics_used["mape"], "r2": metrics_used["r2"],
            "mape_unavailable": metrics_used.get("mape_unavailable", False),
            "validated_on": "Milan" if dominant_regime == "calm" else "Wellington",
        },
    }
