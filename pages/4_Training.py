import streamlit as st
import plotly.graph_objects as go
from sklearn.preprocessing import MinMaxScaler
from src.training import run_optuna, train_full_pipeline

st.title("4. Entraînement — Optuna → GRU → XGBoost")

if "zones" not in st.session_state:
    st.warning("Fais d'abord le split à l'étape 3 (Split).")
    st.stop()

zones = st.session_state["zones"]
features = st.session_state["features"]
target_col = st.session_state["config"]["target_col"]

n_trials = st.slider("Essais Optuna (25 = quelques minutes sur CPU)", 10, 50, 25)

if st.button("🚀 Lancer le pipeline complet"):
    scX = MinMaxScaler().fit(zones["gru_train"][features])
    scY = MinMaxScaler().fit(zones["gru_train"][[target_col]])

    st.subheader("Phase 1 — Recherche Optuna")
    optuna_chart = st.empty()
    optuna_bar = st.progress(0)
    history = []

    def on_trial(num, total, best):
        history.append(best)
        optuna_bar.progress(num / total)
        fig = go.Figure(go.Scatter(y=history, mode="lines+markers"))
        fig.update_layout(xaxis_title="Essai", yaxis_title="Meilleure loss de validation", height=300)
        optuna_chart.plotly_chart(fig, use_container_width=True)

    best_params = run_optuna(zones, features, target_col, scX, scY, n_trials, trial_callback=on_trial)
    st.success(f"Meilleurs hyperparamètres : {best_params}")

    st.subheader("Phase 2 — Entraînement final GRU + XGBoost")
    loss_chart = st.empty()
    loss_history = []

    def on_epoch(epoch, val_loss):
        loss_history.append(val_loss)
        fig = go.Figure(go.Scatter(y=loss_history, mode="lines"))
        fig.update_layout(xaxis_title="Époque", yaxis_title="Loss validation", height=300)
        loss_chart.plotly_chart(fig, use_container_width=True)

    with st.spinner("Entraînement final en cours..."):
        results = train_full_pipeline(zones, features, target_col, best_params, scX, scY, epoch_callback=on_epoch)

    st.session_state["results"] = results
    st.session_state["best_params"] = best_params
    st.success("✅ Pipeline entraîné — va voir le Dashboard (étape 5) pour les métriques.")