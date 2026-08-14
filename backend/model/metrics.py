"""MAE/RMSE/MAPE/R2 always computed and returned together — never a single
metric in isolation (project non-negotiable). Ported from src/metrics.py."""
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def compute_metrics(true, pred):
    true = np.asarray(true, dtype=float)
    pred = np.asarray(pred, dtype=float)
    if len(true) == 0:
        return {"mae": None, "rmse": None, "mape": None, "r2": None, "n": 0, "mape_unavailable": True}
    mae = float(mean_absolute_error(true, pred))
    rmse = float(np.sqrt(mean_squared_error(true, pred)))
    mask = true > 1.0
    mape_unavailable = bool(mask.sum() == 0)
    mape = float(np.abs((true[mask] - pred[mask]) / true[mask]).mean() * 100) if not mape_unavailable else None
    r2 = float(r2_score(true, pred)) if len(true) > 1 else None
    return {"mae": mae, "rmse": rmse, "mape": mape, "r2": r2, "n": int(len(true)), "mape_unavailable": mape_unavailable}
