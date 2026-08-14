"""Recherche du meilleur modèle pour le régime vent calme (<10 m/s), à partir
de zéro : pas d'hypothèse GRU par défaut, comparaison de familles de modèles
différentes sur Bordeaux + Milan (proxy vent calme)."""
import os
import sys
import json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

sys.path.append(os.path.dirname(__file__))
from data_calm import load_site
from features_calm import build_features, TARGET
from split_calm import causal_split
from models_calm import (GRUModel, LSTMModel, TinyTransformer,
                          make_windows, train_sequence_model, predict_sequence)

CACHE_DIR = os.path.dirname(__file__)
CALM_THRESHOLD = 10.0
WINDOWS_TO_TRY = [3, 6, 12]


def metrics(true, pred):
    if len(true) == 0:
        return dict(MAE=np.nan, RMSE=np.nan, MAPE=np.nan, R2=np.nan, n=0)
    mae = mean_absolute_error(true, pred)
    rmse = np.sqrt(mean_squared_error(true, pred))
    mask = true > 1.0
    mape = np.abs((true[mask] - pred[mask]) / true[mask]).mean() * 100 if mask.sum() > 0 else np.nan
    r2 = r2_score(true, pred) if len(true) > 1 else np.nan
    return dict(MAE=mae, RMSE=rmse, MAPE=mape, R2=r2, n=len(true))


def run_site(name):
    print(f"\n{'='*60}\nSite: {name}\n{'='*60}")
    raw = load_site(name, CACHE_DIR)
    print(f"{len(raw)} lignes brutes, vitesse moyenne {raw['wind_speed'].mean():.2f} m/s, "
          f"% sous {CALM_THRESHOLD}m/s: {(raw['wind_speed']<CALM_THRESHOLD).mean()*100:.1f}%")

    df_ext, feats = build_features(raw)
    zones = causal_split(df_ext.reset_index())

    scX = MinMaxScaler().fit(zones["train"][feats])
    scY = MinMaxScaler().fit(zones["train"][[TARGET]])

    def prep(z):
        return scX.transform(z[feats]).astype(np.float32), scY.transform(z[[TARGET]]).astype(np.float32).flatten()

    X_tr, y_tr = prep(zones["train"])
    X_va, y_va = prep(zones["val"])
    X_te, y_te = prep(zones["test"])
    thresh_scaled = scY.transform([[CALM_THRESHOLD]])[0, 0]

    results = {}

    # ---------- 1. Baseline persistance (t+1 = t), évaluée seulement sur cible calme ----------
    calm_mask_te = zones["test"][TARGET] < CALM_THRESHOLD
    persist_pred = zones["test"][f"{TARGET}_lag1"][calm_mask_te].values
    persist_true = zones["test"][TARGET][calm_mask_te].values
    results["persistence"] = metrics(persist_true, persist_pred)

    # ---------- 2. XGBoost tabulaire, entraîné uniquement sur lignes calmes ----------
    calm_tr = zones["train"][TARGET] < CALM_THRESHOLD
    calm_va = zones["val"][TARGET] < CALM_THRESHOLD
    Xg_tr, yg_tr = X_tr[calm_tr.values], y_tr[calm_tr.values]
    Xg_va, yg_va = X_va[calm_va.values], y_va[calm_va.values]
    Xg_te, yg_te = X_te[calm_mask_te.values], y_te[calm_mask_te.values]

    xgb_model = xgb.XGBRegressor(n_estimators=800, max_depth=4, learning_rate=0.05,
                                  subsample=0.8, colsample_bytree=0.8,
                                  reg_alpha=0.5, reg_lambda=2.0,
                                  random_state=42, n_jobs=-1, early_stopping_rounds=30)
    xgb_model.fit(Xg_tr, yg_tr, eval_set=[(Xg_va, yg_va)], verbose=False)
    pred_scaled = xgb_model.predict(Xg_te)
    pred = scY.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
    true = scY.inverse_transform(yg_te.reshape(-1, 1)).flatten()
    results["xgboost_calm_only"] = metrics(true, pred)

    # ---------- 3. Modèles séquentiels (GRU / LSTM / Transformer), fenêtres courtes ----------
    seq_models = {"GRU": GRUModel, "LSTM": LSTMModel, "Transformer": TinyTransformer}
    best_seq = {}
    for model_name, cls in seq_models.items():
        best_for_model = None
        for w in WINDOWS_TO_TRY:
            Xw_tr, yw_tr = make_windows(X_tr, y_tr, w)
            Xw_va, yw_va = make_windows(X_va, y_va, w)
            Xw_te, yw_te = make_windows(X_te, y_te, w)

            m_tr, m_va, m_te = yw_tr < thresh_scaled, yw_va < thresh_scaled, yw_te < thresh_scaled
            if m_tr.sum() < 200 or m_va.sum() < 30 or m_te.sum() < 30:
                continue

            kwargs = dict(hidden=64, layers=1, dropout=0.1) if model_name != "Transformer" \
                else dict(d_model=32, nhead=4, layers=1, dropout=0.1)
            model = train_sequence_model(cls, Xw_tr[m_tr], yw_tr[m_tr], Xw_va[m_va], yw_va[m_va],
                                          n_features=len(feats), **kwargs)
            pred_s, true_s = predict_sequence(model, Xw_te[m_te], yw_te[m_te])
            pred = scY.inverse_transform(pred_s.reshape(-1, 1)).flatten()
            true = scY.inverse_transform(true_s.reshape(-1, 1)).flatten()
            m = metrics(true, pred)
            m["window"] = w
            if best_for_model is None or m["MAE"] < best_for_model["MAE"]:
                best_for_model = m
        if best_for_model:
            results[model_name] = best_for_model

    print(f"\n--- Résultats {name} (test, régime calme <{CALM_THRESHOLD} m/s) ---")
    for k, v in results.items():
        w = f", window={v['window']}h" if "window" in v else ""
        print(f"{k:20s} MAE={v['MAE']:.3f}  RMSE={v['RMSE']:.3f}  MAPE={v['MAPE']:.2f}%  "
              f"R2={v['R2']:.4f}  n={v['n']}{w}")
    return results


if __name__ == "__main__":
    all_results = {}
    for site in ["bordeaux", "milan"]:
        all_results[site] = run_site(site)
    with open(os.path.join(CACHE_DIR, "results_calm_v2.json"), "w") as f:
        json.dump(all_results, f, indent=2, default=float)
    print("\nRésultats sauvegardés dans results_calm_v2.json")
