import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.preprocessing import build_features, detect_frequency

st.title("2. Feature engineering")

if "config" not in st.session_state:
    st.warning("Confirme d'abord le mapping à l'étape 1 (Import).")
    st.stop()

df = st.session_state["raw_df"]
cfg = st.session_state["config"]
freq = detect_frequency(df, cfg["datetime_col"])
st.info(f"Fréquence détectée : **{freq}** — les options ci-dessous sont pré-réglées en conséquence.")

default_lags = [1, 2, 3] if freq == "hourly" else [1, 2]
default_roll = [6, 24] if freq == "hourly" else [3, 7]

lags = st.multiselect("Lags à générer", [1,2,3,6,12,24], default=default_lags)
rolling = st.multiselect("Fenêtres de moyenne glissante", [3,6,12,24,48], default=default_roll)
add_cyclic = st.checkbox("Encodages cycliques temporels", value=(freq in ("hourly", "daily")))

if st.button("Générer les features"):
    df_ext, features, freq = build_features(
        df, cfg["datetime_col"], cfg["target_col"], cfg["feature_cols"],
        lags=lags, rolling_windows=rolling, add_cyclic=add_cyclic)
    st.session_state["df_ext"] = df_ext
    st.session_state["features"] = features
    st.success(f"{len(features)} features générées · {len(df_ext):,} lignes après nettoyage.")
    st.dataframe(df_ext[features + [cfg["target_col"]]].head())

    # ── NOUVEAU : diagnostic de distribution, avant de lancer Optuna ──
    # Bornes calibrées vent (m/s) — à adapter si la cible n'est pas une vitesse de vent.
    st.subheader("Distribution de la cible — un site adapté pour ce cas d'usage ?")
    target_values = df_ext[cfg["target_col"]]
    bins = [0, 5, 10, 15, 20, 25, float('inf')]
    labels = ['0-5', '5-10', '10-15', '15-20', '20-25', '25+']
    value_bin = pd.cut(target_values, bins=bins, labels=labels)
    counts = value_bin.value_counts().reindex(labels)
    pct = (counts / counts.sum() * 100).round(1)

    fig_dist = go.Figure(go.Bar(x=labels, y=counts.values,
                                  text=[f"{p}%" for p in pct.values], textposition="outside"))
    fig_dist.update_layout(title="Répartition des valeurs de la cible", height=300,
                            yaxis_title="Nombre d'heures")
    st.plotly_chart(fig_dist, use_container_width=True)

    
    # Dans pages/2_Features.py, remplace le bloc pct_low par :
    n_above_10 = counts[['10-15', '15-20', '20-25', '25+']].sum()

    if n_above_10 < 200:
        st.warning(
         f"⚠️ Seulement {n_above_10:.0f} points au-dessus de 10 m/s. "
         f"Les métriques dans cette zone (Dashboard) seront peu fiables — "
            f"volume insuffisant plutôt que problème de méthode."
     )
    elif pct_low > 80:
        st.info(
         f"ℹ️ {pct_low:.0f}% des données sous 10 m/s, mais {n_above_10:.0f} points "
         f"restent disponibles au-dessus — suffisant pour une évaluation "
         f"raisonnable des tranches hautes, contrairement à un site plus calme."
     )
    else:
        st.success(f"✓ Distribution équilibrée — {pct_low:.0f}% sous 10 m/s.")