"""Retrain a Milan-only calm-regime XGBoost model. The existing
calm_wind_v2/xgb_calm_milan.json was tuned jointly across Bordeaux+Milan
(hyperparameters chosen to average well over both); this retrains standalone
on Milan alone for a clean, single-site validated story, reusing tune_xgb.py's
Optuna search shape and split_calm.py's CALM_THRESHOLD filtering."""
import os
import json
import numpy as np
import optuna
import xgboost as xgb
from sklearn.preprocessing import MinMaxScaler

from model.data import load_site
from model.features_calm import build_features, TARGET
from model.split import causal_split_3way
from model.metrics import compute_metrics

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "weights")
CALM_THRESHOLD = 10.0
optuna.logging.set_verbosity(optuna.logging.WARNING)


def prep_site():
    raw = load_site("milan")
    df_ext, feats = build_features(raw)
    zones = causal_split_3way(df_ext.reset_index())
    scX = MinMaxScaler().fit(zones["train"][feats])
    scY = MinMaxScaler().fit(zones["train"][[TARGET]])

    def prep(z):
        calm = z[TARGET] < CALM_THRESHOLD
        X = scX.transform(z.loc[calm, feats]).astype(np.float32)
        y = scY.transform(z.loc[calm, [TARGET]]).astype(np.float32).flatten()
        return X, y

    return prep(zones["train"]), prep(zones["val"]), prep(zones["test"]), scX, scY, feats


def run(n_trials=25):
    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    (X_tr, y_tr), (X_va, y_va), (X_te, y_te), scX, scY, feats = prep_site()

    def objective(trial):
        params = dict(
            n_estimators=1000,
            max_depth=trial.suggest_int("max_depth", 2, 6),
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            subsample=trial.suggest_float("subsample", 0.5, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),
            reg_alpha=trial.suggest_float("reg_alpha", 0.0, 2.0),
            reg_lambda=trial.suggest_float("reg_lambda", 0.5, 5.0),
            min_child_weight=trial.suggest_int("min_child_weight", 1, 10),
            random_state=42, n_jobs=-1, early_stopping_rounds=30,
        )
        model = xgb.XGBRegressor(**params)
        model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
        pred = scY.inverse_transform(model.predict(X_va).reshape(-1, 1)).flatten()
        true = scY.inverse_transform(y_va.reshape(-1, 1)).flatten()
        return compute_metrics(true, pred)["mae"]

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials)
    print("Best params:", study.best_params)
    print("Best val MAE:", study.best_value)

    model = xgb.XGBRegressor(n_estimators=1000, random_state=42, n_jobs=-1,
                              early_stopping_rounds=30, **study.best_params)
    model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
    pred = scY.inverse_transform(model.predict(X_te).reshape(-1, 1)).flatten()
    true = scY.inverse_transform(y_te.reshape(-1, 1)).flatten()
    m = compute_metrics(true, pred)
    print(f"TEST milan calm: MAE={m['mae']:.3f} RMSE={m['rmse']:.3f} MAPE={m['mape']:.2f}% R2={m['r2']:.4f} n={m['n']}")

    model.save_model(os.path.join(WEIGHTS_DIR, "xgb_calm_milan.json"))
    import joblib
    joblib.dump({"scaler_X": scX, "scaler_y": scY, "features": feats}, os.path.join(WEIGHTS_DIR, "calm_milan_meta.pkl"))
    with open(os.path.join(WEIGHTS_DIR, "calm_milan_metrics.json"), "w") as f:
        json.dump({"best_params": study.best_params, "test_metrics": m}, f, indent=2, default=float)
    return m


if __name__ == "__main__":
    run()
