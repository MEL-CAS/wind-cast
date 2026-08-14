"""Train the strong-regime GRU + XGBoost-residual-correction pipeline on
Wellington, ported from src/training.py (architecture, losses, reweighting,
seeds all unchanged). This is the first time this pipeline is ever persisted
to disk in this codebase — src/training.py only ever kept the trained model
in Streamlit session_state."""
import os
import json
import numpy as np
import torch
import optuna
import xgboost as xgb
import joblib
from numpy.lib.stride_tricks import sliding_window_view
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import DataLoader, WeightedRandomSampler

from model.data import load_site
from model.features_strong import build_features, TARGET
from model.split import causal_split_5zone
from model.gru import WindDataset, GRUModel, AsymmetricMSELoss
from model.metrics import compute_metrics

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "weights")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
optuna.logging.set_verbosity(optuna.logging.WARNING)


def prep(dd, features, scX, scY):
    return (scX.transform(dd[features]).astype(np.float32),
            scY.transform(dd[[TARGET]]).astype(np.float32))


def compute_sample_weights(target_values, n_bins=20):
    counts, edges = np.histogram(target_values, bins=n_bins)
    bin_idx = np.clip(np.digitize(target_values, edges[:-1]) - 1, 0, n_bins - 1)
    return 1.0 / (counts[bin_idx] + 1)


def run_optuna(zones, features, scX, scY, n_trials=20, search_epochs=3, max_search_rows=6000):
    torch.set_num_threads(4)
    train_zone = zones["gru_train"].tail(max_search_rows) if len(zones["gru_train"]) > max_search_rows else zones["gru_train"]
    X_tr_full, y_tr_full = prep(train_zone, features, scX, scY)
    X_es_full, y_es_full = prep(zones["gru_earlystop"], features, scX, scY)
    window_cache = {}

    def get_windows(w):
        if w not in window_cache:
            def make(X, y):
                Xw = sliding_window_view(X, w, axis=0)
                Xw = np.moveaxis(Xw, -1, 1)[:-1]
                yw = y[w:]
                return (torch.from_numpy(Xw.copy()), torch.from_numpy(yw.copy()))
            window_cache[w] = (make(X_tr_full, y_tr_full), make(X_es_full, y_es_full))
        return window_cache[w]

    def objective(trial):
        hidden = trial.suggest_categorical("hidden", [32, 64, 128, 256])
        layers = trial.suggest_int("layers", 1, 2)
        dropout = trial.suggest_float("dropout", 0.0, 0.3)
        lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
        batch_size = trial.suggest_categorical("batch_size", [64, 128, 256])
        window = trial.suggest_categorical("window", [12, 20, 24, 48])

        (Xw_tr, yw_tr), (Xw_es, yw_es) = get_windows(window)
        N = len(Xw_tr)

        torch.manual_seed(42)
        model = GRUModel(len(features), hidden, layers, dropout).to(DEVICE)
        opt = torch.optim.Adam(model.parameters(), lr=lr)
        crit = AsymmetricMSELoss(1.5)

        for epoch in range(search_epochs):
            model.train()
            perm = torch.randperm(N)
            for start in range(0, N, batch_size):
                idx = perm[start:start + batch_size]
                xb, yb = Xw_tr[idx].to(DEVICE), yw_tr[idx].to(DEVICE)
                opt.zero_grad(); crit(model(xb), yb).backward(); opt.step()

        model.eval()
        with torch.no_grad():
            val_loss = crit(model(Xw_es.to(DEVICE)), yw_es.to(DEVICE)).item()
        return val_loss

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials)
    return study.best_params


def train_full_pipeline(zones, features, best_params, scX, scY, reweight=True):
    W = best_params["window"]

    X_tr, y_tr = prep(zones["gru_train"], features, scX, scY)
    X_es, y_es = prep(zones["gru_earlystop"], features, scX, scY)
    X_xtr, y_xtr = prep(zones["xgb_train"], features, scX, scY)
    X_xes, y_xes = prep(zones["xgb_earlystop"], features, scX, scY)
    X_tst, y_tst = prep(zones["test"], features, scX, scY)

    if reweight:
        sample_weights = compute_sample_weights(zones["gru_train"][TARGET].values[W:])
        sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)
        dl_tr = DataLoader(WindDataset(X_tr, y_tr, W), batch_size=best_params["batch_size"], sampler=sampler)
    else:
        dl_tr = DataLoader(WindDataset(X_tr, y_tr, W), batch_size=best_params["batch_size"], shuffle=True)

    dl_es = DataLoader(WindDataset(X_es, y_es, W), batch_size=256, shuffle=False)
    dl_xtr = DataLoader(WindDataset(X_xtr, y_xtr, W), batch_size=256, shuffle=False)
    dl_xes = DataLoader(WindDataset(X_xes, y_xes, W), batch_size=256, shuffle=False)
    dl_tst = DataLoader(WindDataset(X_tst, y_tst, W), batch_size=256, shuffle=False)

    torch.manual_seed(42)
    model = GRUModel(len(features), best_params["hidden"], best_params["layers"], best_params["dropout"]).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=best_params["lr"])
    crit = AsymmetricMSELoss(1.5)
    best_val, patience, best_state = float("inf"), 0, None

    for epoch in range(150):
        model.train()
        for xb, yb in dl_tr:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            opt.zero_grad(); crit(model(xb), yb).backward(); opt.step()
        model.eval()
        vl = np.mean([crit(model(xb.to(DEVICE)), yb.to(DEVICE)).item() for xb, yb in dl_es])
        if vl < best_val:
            best_val, patience, best_state = vl, 0, {k: v.clone() for k, v in model.state_dict().items()}
        else:
            patience += 1
            if patience >= 20:
                break
    model.load_state_dict(best_state)

    def predict(loader):
        model.eval(); P, T = [], []
        with torch.no_grad():
            for xb, yb in loader:
                P.append(model(xb.to(DEVICE)).cpu().numpy()); T.append(yb.numpy())
        return (scY.inverse_transform(np.concatenate(P)).flatten(),
                scY.inverse_transform(np.concatenate(T)).flatten())

    pred_xtr, true_xtr = predict(dl_xtr)
    pred_xes, true_xes = predict(dl_xes)
    pred_tst, true_tst = predict(dl_tst)
    res_xtr, res_xes = true_xtr - pred_xtr, true_xes - pred_xes

    def build_xgb_features(X_raw, pred_gru):
        feats = X_raw[W - 1:-1]
        grad = np.zeros_like(pred_gru)
        grad[1:] = pred_gru[1:] - pred_gru[:-1]
        return np.column_stack([feats, pred_gru, grad])

    X_xtr_raw, _ = prep(zones["xgb_train"], features, scX, scY)
    X_xes_raw, _ = prep(zones["xgb_earlystop"], features, scX, scY)
    X_tst_raw, _ = prep(zones["test"], features, scX, scY)

    xgb_model = xgb.XGBRegressor(
        n_estimators=1000, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.5, reg_lambda=2.0,
        random_state=42, n_jobs=-1, early_stopping_rounds=30)

    if reweight:
        w_xtr = np.clip(true_xtr / (true_xtr.mean() + 1e-6), 0.5, 5.0)
        xgb_model.fit(build_xgb_features(X_xtr_raw, pred_xtr), res_xtr, sample_weight=w_xtr,
                       eval_set=[(build_xgb_features(X_xes_raw, pred_xes), res_xes)], verbose=False)
    else:
        xgb_model.fit(build_xgb_features(X_xtr_raw, pred_xtr), res_xtr,
                       eval_set=[(build_xgb_features(X_xes_raw, pred_xes), res_xes)], verbose=False)

    correction = xgb_model.predict(build_xgb_features(X_tst_raw, pred_tst))
    pred_combined = pred_tst + correction

    return {
        "model": model, "xgb_model": xgb_model, "window": W,
        "metrics_base": compute_metrics(true_tst, pred_tst),
        "metrics_combined": compute_metrics(true_tst, pred_combined),
    }


def run(n_trials=20):
    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    raw = load_site("wellington")
    df_ext, feats = build_features(raw)
    zones = causal_split_5zone(df_ext.reset_index())

    scX = MinMaxScaler().fit(zones["gru_train"][feats])
    scY = MinMaxScaler().fit(zones["gru_train"][[TARGET]])

    print("Running Optuna search...")
    best_params = run_optuna(zones, feats, scX, scY, n_trials=n_trials)
    print("Best params:", best_params)

    print("Training final pipeline...")
    result = train_full_pipeline(zones, feats, best_params, scX, scY, reweight=True)
    m_base, m_combined = result["metrics_base"], result["metrics_combined"]
    print(f"GRU-only:  MAE={m_base['mae']:.3f} RMSE={m_base['rmse']:.3f} MAPE={m_base['mape']:.2f}% R2={m_base['r2']:.4f}")
    print(f"GRU+XGB:   MAE={m_combined['mae']:.3f} RMSE={m_combined['rmse']:.3f} MAPE={m_combined['mape']:.2f}% R2={m_combined['r2']:.4f}")

    torch.save(result["model"].state_dict(), os.path.join(WEIGHTS_DIR, "gru_wellington.pt"))
    result["xgb_model"].save_model(os.path.join(WEIGHTS_DIR, "xgb_residual_wellington.json"))
    joblib.dump({
        "scaler_X": scX, "scaler_y": scY, "features": feats, "window": result["window"],
        "gru_params": {k: best_params[k] for k in ("hidden", "layers", "dropout")},
    }, os.path.join(WEIGHTS_DIR, "strong_wellington_meta.pkl"))
    with open(os.path.join(WEIGHTS_DIR, "strong_wellington_metrics.json"), "w") as f:
        json.dump({"best_params": best_params, "metrics_base": m_base, "metrics_combined": m_combined},
                   f, indent=2, default=float)
    return m_combined


if __name__ == "__main__":
    run()
