"""Real regime detection for a 24h forecast timeline. src/model_selector.py
was dead code (never called, placeholder thresholds, one-shot per-dataset
decision, no hysteresis). This replaces it with an actual state machine
applied hour-by-hour so the calm/strong timeline doesn't flap on borderline
readings.

Hysteresis: switch calm->strong only above UPPER, strong->calm only below
LOWER. Inside the band, the previous state is kept."""

THRESHOLD = 10.0
UPPER = 10.5
LOWER = 9.5


def classify_hourly(wind_speeds, initial_regime=None):
    """wind_speeds: list/array of predicted m/s, chronological.
    Returns list of 'calm'/'strong', same length, hysteresis-stabilized."""
    regimes = []
    state = initial_regime or ("strong" if wind_speeds[0] >= THRESHOLD else "calm")
    for v in wind_speeds:
        if state == "calm" and v >= UPPER:
            state = "strong"
        elif state == "strong" and v <= LOWER:
            state = "calm"
        regimes.append(state)
    return regimes


def select_model_for_regime(regime):
    """Which trained model handles this hour. 'strong' regime hours use the
    Wellington GRU+XGBoost pipeline; 'calm' hours use the Milan XGBoost
    calm-only model."""
    return "strong" if regime == "strong" else "calm"


def summarize_dual_usage(regimes):
    """model_used field for the API contract: 'calm'/'strong' if the whole
    24h horizon stays in one regime, 'dual' if it switches."""
    uniq = set(regimes)
    if uniq == {"calm"}:
        return "calm"
    if uniq == {"strong"}:
        return "strong"
    return "dual"
