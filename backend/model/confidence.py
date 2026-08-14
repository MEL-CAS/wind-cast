"""Confidence scoring — no prior implementation exists anywhere in the
codebase, this is designed fresh (project non-negotiable: never present
precision as uniform across sites; unvalidated sites get hedged language).

score = validated_base_accuracy
        x site_similarity   (how close the query site's recent wind stats are
                              to the validated site's historical distribution)
        x horizon_decay     (confidence shrinks over the 24h horizon)
        x regime_stability  (fewer hysteresis flips = more confidence)
"""

# Historical mean/std (m/s) of the validated sites, computed from their
# training data — used as the reference distribution for site_similarity.
VALIDATED_STATS = {
    "calm": {"site": "Milan", "mean": 3.28, "std": 2.24},
    "strong": {"site": "Wellington", "mean": 9.44, "std": 4.58},
}

# Base accuracy derived from each regime's validated test-set R^2 (filled in
# after training — see model/weights/*_metrics.json). Updated by inference.py
# at load time so this always reflects the actually-trained model, never a
# stale guess.
DEFAULT_BASE_ACCURACY = {"calm": 0.80, "strong": 0.75}


def site_similarity(recent_mean, recent_std, regime):
    ref = VALIDATED_STATS[regime]
    mean_z = abs(recent_mean - ref["mean"]) / (ref["std"] + 1e-6)
    std_ratio = min(recent_std, ref["std"]) / (max(recent_std, ref["std"]) + 1e-6)
    mean_component = max(0.0, 1.0 - mean_z / 3.0)
    return max(0.0, min(1.0, 0.6 * mean_component + 0.4 * std_ratio))


def horizon_decay(hour_index, total_hours=24, floor=0.65):
    frac = hour_index / max(total_hours - 1, 1)
    return 1.0 - (1.0 - floor) * frac


def regime_stability(regimes):
    if len(regimes) < 2:
        return 1.0
    transitions = sum(1 for a, b in zip(regimes, regimes[1:]) if a != b)
    return max(0.5, 1.0 - transitions / len(regimes))


def compute_confidence(regime, recent_mean, recent_std, regimes_24h, base_accuracy=None):
    """Returns {score, label, reason} for the whole 24h forecast (one score,
    not per-hour, matching the API contract)."""
    base = (base_accuracy or DEFAULT_BASE_ACCURACY)[regime]
    sim = site_similarity(recent_mean, recent_std, regime)
    stab = regime_stability(regimes_24h)
    avg_horizon = sum(horizon_decay(i) for i in range(len(regimes_24h))) / max(len(regimes_24h), 1)

    score = max(0.0, min(1.0, base * (0.4 + 0.6 * sim) * avg_horizon * stab))

    ref = VALIDATED_STATS[regime]
    if score >= 0.7:
        label = "élevée"
        reason = (f"Conditions proches du site de validation {ref['site']} "
                   f"(régime {regime})")
    elif score >= 0.45:
        label = "modérée"
        reason = (f"Conditions partiellement éloignées du site de validation {ref['site']} "
                   "— prévision indicative")
    else:
        label = "faible"
        reason = (f"Site nettement différent du site de validation {ref['site']} "
                   "— confiance faible, prévision indicative uniquement")

    return {"score": round(score, 3), "label": label, "reason": reason}
