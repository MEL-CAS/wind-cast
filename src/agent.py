import pandas as pd
import numpy as np

# Mots-clés métier pour la Règle 2, par ordre de priorité.
TARGET_KEYWORDS = ["speed", "power", "consumption", "demand", "load",
                   "price", "sales", "temperature", "temp", "target", "value"]


def detect_datetime_column(df):
    """Règle 1 : colonne avec le meilleur taux de conversion en datetime."""
    best_col, best_score = None, 0.0
    for col in df.columns:
        if df[col].dtype in ("float64", "int64"):
            continue  # une colonne purement numérique n'est pas une date lisible
        sample = df[col].dropna().head(200)
        if len(sample) == 0:
            continue
        converted = pd.to_datetime(sample, errors="coerce")
        score = converted.notna().mean()
        # bonus si beaucoup de valeurs uniques (une vraie série temporelle ne répète pas ses timestamps)
        uniqueness = sample.nunique() / len(sample)
        if score > 0.9 and score * uniqueness > best_score:
            best_col, best_score = col, score * uniqueness
    return best_col


def suggest_target(df, datetime_col):
    """Règle 2 : mot-clé métier d'abord, variance normalisée sinon."""
    numeric_cols = [c for c in df.select_dtypes(include=np.number).columns
                    if c != datetime_col]
    if not numeric_cols:
        return None, "aucune colonne numérique trouvée"

    for keyword in TARGET_KEYWORDS:
        for col in numeric_cols:
            if keyword in col.lower():
                return col, f"nom contenant le mot-clé métier '{keyword}'"

    # fallback : coefficient de variation le plus élevé (colonne "la plus intéressante à prédire")
    cv = {}
    for col in numeric_cols:
        mean = df[col].mean()
        if abs(mean) > 1e-9:
            cv[col] = df[col].std() / abs(mean)
    if not cv:
        return numeric_cols[0], "première colonne numérique (fallback)"
    best = max(cv, key=cv.get)
    return best, "plus grand coefficient de variation (fallback sans mot-clé)"


def detect_leakage(df, target_col, corr_threshold=0.97):
    """Règles 3 et 4 : corrélation quasi parfaite OU nom trop proche de la cible."""
    suspects = {}
    numeric_cols = [c for c in df.select_dtypes(include=np.number).columns
                    if c != target_col]

    # Règle 3 — corrélation (sur un échantillon pour rester rapide sur de gros fichiers)
    sample = df[[target_col] + numeric_cols].dropna().sample(
        n=min(5000, len(df.dropna())), random_state=42)
    for col in numeric_cols:
        corr = sample[target_col].corr(sample[col])
        if abs(corr) >= corr_threshold:
            suspects[col] = f"corrélation {corr:+.3f} avec la cible (règle 3)"

    # Règle 4 — similarité de nom (la cible sans unités/suffixes est contenue dans le nom)
    root = target_col.lower().replace("_", "")[:8]
    for col in numeric_cols:
        if col in suspects:
            continue
        if len(root) >= 5 and root in col.lower().replace("_", ""):
            suspects[col] = f"nom trop proche de '{target_col}' (règle 4)"
    return suspects


def analyze_dataset(df):
    """Point d'entrée de l'agent : renvoie toutes les suggestions + leurs justifications.
    Ne modifie JAMAIS le dataset — analyse seulement (règle 6 : tout est traçable)."""
    report = {"rules_fired": []}

    dt_col = detect_datetime_column(df)
    report["datetime_column"] = dt_col
    report["rules_fired"].append(
        f"Règle 1 → datetime : '{dt_col}'" if dt_col
        else "Règle 1 → aucune colonne datetime détectée, sélection manuelle requise")

    target, reason = suggest_target(df, dt_col)
    report["target_column"] = target
    report["rules_fired"].append(f"Règle 2 → cible : '{target}' ({reason})")

    suspects = detect_leakage(df, target) if target else {}
    report["suspicious_leakage_columns"] = suspects
    for col, why in suspects.items():
        report["rules_fired"].append(f"⚠ Fuite suspectée : '{col}' — {why}")

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    report["feature_columns"] = [c for c in numeric_cols
                                    if c != target and c not in suspects]
    report["rules_fired"].append(
        f"Règle 5 → {len(report['feature_columns'])} features candidates")
    return report