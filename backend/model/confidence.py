"""Confidence scoring — no prior implementation exists anywhere in the
codebase, this is designed fresh (project non-negotiable: never present
precision as uniform across sites; unvalidated sites get hedged language).

score = validated_base_accuracy
        x site_similarity_factor   (how close the query site's recent wind
                                     stats are to the validated site's
                                     historical distribution)
        x stability_factor         (fewer hysteresis flips = more confidence)

Note: an earlier version also multiplied in a per-hour horizon-decay average.
That over-penalized: three independently-discounting multiplicative factors
compounded so hard that even querying the *exact* validated site only landed
around 55-60% ("modérée") instead of reflecting the model's real ~78-93%
validated accuracy. Horizon uncertainty is a real thing, but it belongs in
the per-hour confidence interval width, not baked into a single headline
number that then reads as "the model doesn't trust itself" — removed here.
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


def regime_stability(regimes):
    """1.0 with no regime switch; a real dual-regime day (one calm<->strong
    transition) is normal, not a modeling failure, so the penalty is mild."""
    if len(regimes) < 2:
        return 1.0
    transitions = sum(1 for a, b in zip(regimes, regimes[1:]) if a != b)
    return max(0.85, 1.0 - 0.03 * transitions)


def compute_confidence(regime, recent_mean, recent_std, regimes_24h, base_accuracy=None):
    """Returns {score, label, reason} for the whole 24h forecast (one score,
    not per-hour, matching the API contract)."""
    base = (base_accuracy or DEFAULT_BASE_ACCURACY)[regime]
    sim = site_similarity(recent_mean, recent_std, regime)
    stab = regime_stability(regimes_24h)
    sim_factor = 0.7 + 0.3 * sim

    score = max(0.0, min(1.0, base * sim_factor * stab))

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
