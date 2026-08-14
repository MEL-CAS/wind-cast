import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def compute_metrics(true, pred):
    """Les 4 métriques ensemble, systématiquement — jamais le MAE isolé."""
    if len(true) == 0:
        return np.nan, np.nan, np.nan, np.nan
    mae = mean_absolute_error(true, pred)
    rmse = np.sqrt(mean_squared_error(true, pred))
    mask = true > 1.0
    mape = np.abs((true[mask] - pred[mask]) / true[mask]).mean() * 100 if mask.sum() > 0 else np.nan
    r2 = r2_score(true, pred) if len(true) > 1 else np.nan
    return mae, rmse, mape, r2


def metrics_by_bin(true, pred, bins=None, labels=None):
    """Les mêmes 4 métriques, découpées par tranche de la cible. Rappel important
    affiché dans le dashboard : le R² par tranche étroite peut devenir très
    négatif — artefact de variance locale, pas un défaut du modèle. MAE/RMSE
    restent les métriques fiables pour comparer les tranches entre elles."""
    if bins is None:
        bins = [0, 5, 10, 15, 20, 25, np.inf]
        labels = ['0-5', '5-10', '10-15', '15-20', '20-25', '25+']
    value_bin = pd.cut(true, bins=bins, labels=labels)
    rows = []
    for label in labels:
        mask = (value_bin == label)
        n = mask.sum()
        if n > 10:
            mae, rmse, mape, r2 = compute_metrics(true[mask], pred[mask])
            rows.append({"Tranche": label, "n": int(n), "MAE": mae, "RMSE": rmse, "MAPE": mape, "R2": r2})
        else:
            rows.append({"Tranche": label, "n": int(n), "MAE": np.nan, "RMSE": np.nan, "MAPE": np.nan, "R2": np.nan})
    return pd.DataFrame(rows)


def permutation_test(true, pred_base, correction, n_permutations=1000, seed=42):
    rng = np.random.default_rng(seed)
    real_mae = mean_absolute_error(true, pred_base + correction)
    permuted = np.array([mean_absolute_error(true, pred_base + rng.permutation(correction))
                          for _ in range(n_permutations)])
    p_value = (permuted <= real_mae).mean()
    return real_mae, permuted, p_value


def constant_baseline(true, pred_base, xgb_train_residuals):
    return mean_absolute_error(true, pred_base + xgb_train_residuals.mean())