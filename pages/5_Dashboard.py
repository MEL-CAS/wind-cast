import streamlit as st
import plotly.graph_objects as go
from src.metrics import compute_metrics, metrics_by_bin, permutation_test, constant_baseline

st.title("5. Tableau de bord")

if "results" not in st.session_state:
    st.warning("Entraîne d'abord le pipeline à l'étape 4 (Training).")
    st.stop()

res = st.session_state["results"]
m = compute_metrics(res["true"], res["pred_combined"])

st.subheader("Métriques générales (test set complet)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("MAE", f"{m[0]:.3f}")
c2.metric("RMSE", f"{m[1]:.3f}")
c3.metric("MAPE", f"{m[2]:.1f}%")
c4.metric("R²", f"{m[3]:.3f}")

st.subheader("Validation automatique (toujours affichée)")
mae_const = constant_baseline(res["true"], res["pred_base"], res["xgb_train_residuals"])
real_mae, permuted, p_value = permutation_test(res["true"], res["pred_base"], res["correction"])

colA, colB = st.columns(2)
colA.metric("MAE vs correction constante", f"{m[0]:.3f} vs {mae_const:.3f}",
            delta=f"{m[0] - mae_const:+.3f}", delta_color="inverse")
colB.metric("Test de permutation", f"p = {p_value:.4f}",
            "significatif" if p_value < 0.05 else "non significatif")

# ── Le gain est-il économiquement significatif, pas seulement statistiquement ? ──
gain_relatif = (mae_const - m[0]) / mae_const * 100 if mae_const > 0 else 0
if p_value < 0.05 and gain_relatif < 3:
    st.info(f"ℹ️ Le gain est statistiquement significatif (p<0.05) mais ne représente que "
            f"{gain_relatif:.1f}% d'amélioration relative par rapport à une simple correction "
            f"constante. Sur un grand nombre de points de test, un effet minuscule peut "
            f"devenir statistiquement significatif sans être économiquement notable.")

fig_perm = go.Figure()
fig_perm.add_histogram(x=permuted, name="MAE permutations")
fig_perm.add_vline(x=real_mae, line_color="red", annotation_text="MAE réel")
fig_perm.update_layout(height=280)
st.plotly_chart(fig_perm, use_container_width=True)

st.subheader("Métriques par tranche de valeur")
st.caption("⚠️ Le R² par tranche étroite peut devenir très négatif — artefact de variance "
           "locale, pas un défaut du modèle. Fie-toi au MAE/RMSE pour comparer les tranches.")
df_bins = metrics_by_bin(res["true"], res["pred_combined"])
st.dataframe(df_bins.style.format({"MAE": "{:.3f}", "RMSE": "{:.3f}",
                                    "MAPE": "{:.2f}%", "R2": "{:.3f}"}),
             use_container_width=True)

# ── NOUVEAU : alerte explicite sur les tranches peu couvertes ──
low_n_bins = df_bins[df_bins["n"] < 30]
if not low_n_bins.empty:
    tranches = ", ".join(low_n_bins["Tranche"].tolist())
    total_low_n = low_n_bins["n"].sum()
    pct_data = (1 - total_low_n / df_bins["n"].sum()) * 100
    st.warning(
        f"⚠️ **Tranches avec moins de 30 points de test — métriques non fiables : {tranches}**\n\n"
        f"Ce site n'a probablement pas assez d'heures dans ces plages pour évaluer "
        f"correctement la performance du modèle. Les métriques générales ci-dessus "
        f"reflètent surtout le comportement sur le reste de la distribution.\n\n"
        f"**Recommandation :** ne pas utiliser ce modèle pour des décisions concernant "
        f"les valeurs élevées tant que davantage de données ne sont pas disponibles pour ces tranches."
    )

fig_bins = go.Figure(go.Bar(x=df_bins["Tranche"], y=df_bins["MAE"]))
fig_bins.update_layout(title="MAE par tranche", height=280)
st.plotly_chart(fig_bins, use_container_width=True)

st.subheader("Prédictions vs réel — test final")
n_show = st.slider("Points affichés", 100, min(2000, len(res["true"])), 500)
fig2 = go.Figure()
fig2.add_scatter(y=res["true"][:n_show], name="Réel", line=dict(width=1.5))
fig2.add_scatter(y=res["pred_combined"][:n_show], name="Prédit", line=dict(width=1.5))
st.plotly_chart(fig2, use_container_width=True)