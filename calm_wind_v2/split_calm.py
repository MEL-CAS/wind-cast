"""Split causal (chronologique, pas de shuffle). Le filtrage au régime calme
se fait APRÈS, séparément pour les modèles tabulaires (filtrage direct des
lignes, chaque ligne porte déjà son historique via les features de lag) et
pour les modèles séquentiels (filtrage après construction des fenêtres, pour
ne jamais construire une fenêtre à partir d'heures non consécutives)."""

CALM_THRESHOLD = 10.0  # m/s


def causal_split(df, p_train=0.70, p_val=0.10, p_test=0.20):
    n = len(df)
    c1 = int(n * p_train)
    c2 = int(n * (p_train + p_val))
    return {
        "train": df.iloc[:c1].reset_index(drop=True),
        "val": df.iloc[c1:c2].reset_index(drop=True),
        "test": df.iloc[c2:].reset_index(drop=True),
    }
