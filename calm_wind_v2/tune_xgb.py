"""XGBoost gagne nettement le comparatif (run_compare.py) sur le régime calme.
On affine ses hyperparamètres avec Optuna avant de le retenir définitivement."""
import os
import sys
import json
import numpy as np
import optuna
import xgboost as xgb
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

sys.path.append(os.path.dirname(__file__))
from data_calm import load_site
from features_calm import build_features, TARGET
from split_calm import causal_split

CACHE_DIR = os.path.dirname(__file__)
CALM_THRESHOLD = 10.0
optuna.logging.set_verbosity(optuna.logging.WARNING)


def metrics(true, pred):
    mae = mean_absolute_error(true, pred)
    rmse = np.sqrt(mean_squared_error(true, pred))
    mask = true > 1.0
    mape = np.abs((true[mask] - pred[mask]) / true[mask]).mean() * 100
    r2 = r2_score(true, pred)
    return dict(MAE=mae, RMSE=rmse, MAPE=mape, R2=r2, n=len(true))


def prep_site(name):
    raw = load_site(name, CACHE_DIR)
    df_ext, feats = build_features(raw)
    zones = causal_split(df_ext.reset_index())
    scX = MinMaxScaler().fit(zones["train"][feats])
    scY = MinMaxScaler().fit(zones["train"][[TARGET]])

    def prep(z):
        calm = z[TARGET] < CALM_THRESHOLD
        X = scX.transform(z.loc[calm, feats]).astype(np.float32)
        y = scY.transform(z.loc[calm, [TARGET]]).astype(np.float32).flatten()
        return X, y

    return prep(zones["train"]), prep(zones["val"]), prep(zones["test"]), scX, scY, feats


SITES = ["bordeaux", "milan"]
DATA = {s: prep_site(s) for s in SITES}


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
    # optimise la moyenne des MAE (unités réelles) sur les DEUX sites — évite un
    # modèle qui surperforme un site et sous-performe l'autre
    maes = []
    for s in SITES:
        (X_tr, y_tr), (X_va, y_va), (X_te, y_te), scX, scY, feats = DATA[s]
        model = xgb.XGBRegressor(**params)
        model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
        pred = scY.inverse_transform(model.predict(X_va).reshape(-1, 1)).flatten()
        true = scY.inverse_transform(y_va.reshape(-1, 1)).flatten()
        maes.append(mean_absolute_error(true, pred))
    return float(np.mean(maes))


if __name__ == "__main__":
    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=25)
    print("Meilleurs hyperparamètres :", study.best_params)
    print("MAE val moyen (2 sites) :", study.best_value)

    final_results = {}
    for s in SITES:
        (X_tr, y_tr), (X_va, y_va), (X_te, y_te), scX, scY, feats = DATA[s]
        model = xgb.XGBRegressor(n_estimators=1000, random_state=42, n_jobs=-1,
                                  early_stopping_rounds=30, **study.best_params)
        model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
        pred = scY.inverse_transform(model.predict(X_te).reshape(-1, 1)).flatten()
        true = scY.inverse_transform(y_te.reshape(-1, 1)).flatten()
        m = metrics(true, pred)
        final_results[s] = m
        print(f"{s}: MAE={m['MAE']:.3f} RMSE={m['RMSE']:.3f} MAPE={m['MAPE']:.2f}% R2={m['R2']:.4f} n={m['n']}")
        model.save_model(os.path.join(CACHE_DIR, f"xgb_calm_{s}.json"))

    with open(os.path.join(CACHE_DIR, "xgb_calm_best_params.json"), "w") as f:
        json.dump({"best_params": study.best_params, "test_results": final_results}, f, indent=2, default=float)
