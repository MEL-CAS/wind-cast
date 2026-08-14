import pandas as pd
import numpy as np

# ── Seuils PLACEHOLDER — à remplacer par les valeurs du balayage (section 3) ──
# Exemple si le sweep donne : Milan (calme gagne) à X%, Saint-Nazaire (base gagne) à 84.3%
THRESHOLD_CALM = 90.0   # au-dessus : le modèle calme gagne clairement (à ajuster)
THRESHOLD_BASE = 85.0   # en dessous : le modèle de base gagne clairement (à ajuster)


def measure_wind_distribution(df, target_col):
    """Retourne (pct_low, n_above_10) pour un dataset donné."""
    bins = [0, 5, 10, 15, 20, 25, np.inf]
    labels = ['0-5', '5-10', '10-15', '15-20', '20-25', '25+']
    value_bin = pd.cut(df[target_col], bins=bins, labels=labels)
    counts = value_bin.value_counts().reindex(labels).fillna(0)
    pct_low = float(counts[['0-5', '5-10']].sum() / counts.sum() * 100)
    n_above_10 = int(counts[['10-15', '15-20', '20-25', '25+']].sum())
    return pct_low, n_above_10


def select_model(pct_low, n_above_10):
    """Décision STATIQUE — appelée une fois au Training, jamais reconsidérée
    ensuite (pas de bascule en cours de route, pas de logique en Live)."""
    if pct_low >= THRESHOLD_CALM:
        return "calm", (
            f"{pct_low:.0f}% des données sous 10 m/s (\u2265{THRESHOLD_CALM}%) \u2014 "
            f"modèle calme sélectionné (fenêtres courtes, validé sur Bordeaux et Milan).")
    elif pct_low <= THRESHOLD_BASE:
        return "base", (
            f"{pct_low:.0f}% des données sous 10 m/s (\u2264{THRESHOLD_BASE}%) \u2014 "
            f"modèle de base sélectionné (référence validée S15).")
    else:
        return "uncertain", (
            f"{pct_low:.0f}% des données sous 10 m/s \u2014 entre les deux seuils "
            f"({THRESHOLD_BASE}\u2013{THRESHOLD_CALM}%). Aucun des deux modèles n'est "
            f"clairement le mieux adapté ; le modèle de base est utilisé par défaut, "
            f"mais les résultats sur ce site méritent une lecture prudente \u2014 "
            f"envisage de tester les deux modèles et de comparer.")