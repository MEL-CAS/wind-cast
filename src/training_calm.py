import time
import numpy as np
import torch
import optuna
import xgboost as xgb
from numpy.lib.stride_tricks import sliding_window_view
from torch.utils.data import DataLoader
from src.model import WindDataset, GRUModel, AsymmetricMSELoss

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

CALM_WINDOW_CHOICES = [3, 6, 12, 20]  # hypothèse PACF — fenêtres courtes prioritaires


def prep(dd, features, target_col, scX, scY):
    return (scX.transform(dd[features]).astype(np.float32),
            scY.transform(dd[[target_col]]).astype(np.float32))


def run_optuna_calm(zones, features, target_col, scX, scY, n_trials=15, trial_callback=None,
                     search_epochs=3, max_search_rows=6000):
    """Identique à run_optuna() du modèle de base, sauf l'espace de recherche de
    `window`, restreint aux fenêtres courtes justifiées par le diagnostic PACF
    du régime calme."""
    torch.set_num_threads(4)

    train_zone = zones["gru_train"].tail(max_search_rows) if len(zones["gru_train"]) > max_search_rows else zones["gru_train"]
    X_tr_full, y_tr_full = prep(train_zone, features, target_col, scX, scY)
    X_es_full, y_es_full = prep(zones["gru_earlystop"], features, target_col, scX, scY)

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
        window = trial.suggest_categorical("window", CALM_WINDOW_CHOICES)

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

    def cb(study, trial):
        if trial_callback:
            trial_callback(trial.number + 1, n_trials, study.best_value)

    study.optimize(objective, n_trials=n_trials, callbacks=[cb])
    print(f"Meilleurs hyperparamètres (calme) : {study.best_params}")
    return study.best_params


def train_full_pipeline_calm(zones, features, target_col, best_params, scX, scY, epoch_callback=None):
    """Identique à train_full_pipeline() du modèle de base — même architecture,
    même loss, même correction XGBoost avec décalage causal. Aucune
    repondération : rejetée empiriquement (Bordeaux + Saint-Nazaire, tableau
    récapitulatif de la comparaison avec/sans), pas réintroduite ici."""
    W = best_params["window"]

    X_tr, y_tr = prep(zones["gru_train"], features, target_col, scX, scY)
    X_es, y_es = prep(zones["gru_earlystop"], features, target_col, scX, scY)
    X_xtr, y_xtr = prep(zones["xgb_train"], features, target_col, scX, scY)
    X_xes, y_xes = prep(zones["xgb_earlystop"], features, target_col, scX, scY)
    X_tst, y_tst = prep(zones["test"], features, target_col, scX, scY)

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
        if epoch_callback:
            epoch_callback(epoch + 1, vl)
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
        feats = X_raw[W-1:-1]
        grad = np.zeros_like(pred_gru)
        grad[1:] = pred_gru[1:] - pred_gru[:-1]
        return np.column_stack([feats, pred_gru, grad])

    X_xtr_raw, _ = prep(zones["xgb_train"], features, target_col, scX, scY)
    X_xes_raw, _ = prep(zones["xgb_earlystop"], features, target_col, scX, scY)
    X_tst_raw, _ = prep(zones["test"], features, target_col, scX, scY)

    xgb_model = xgb.XGBRegressor(
        n_estimators=1000, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.5, reg_lambda=2.0,
        random_state=42, n_jobs=-1, early_stopping_rounds=30)
    xgb_model.fit(build_xgb_features(X_xtr_raw, pred_xtr), res_xtr,
                   eval_set=[(build_xgb_features(X_xes_raw, pred_xes), res_xes)], verbose=False)

    correction = xgb_model.predict(build_xgb_features(X_tst_raw, pred_tst))
    return {
        "model": model, "xgb_model": xgb_model,
        "scaler_X": scX, "scaler_y": scY, "window": W,
        "true": true_tst, "pred_base": pred_tst,
        "correction": correction,
        "pred_combined": pred_tst + correction,
        "xgb_train_residuals": res_xtr,
    }