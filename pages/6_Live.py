import streamlit as st
import plotly.graph_objects as go
from src.live import fetch_live_wind, predict_next_hour

st.title("6. Monitoring en direct")

if "results" not in st.session_state:
    st.warning("Entraîne d'abord un modèle (étape 4).")
    st.stop()

LIVE_FEATURES = {"wind_speed_100m_approx", "wind_speed_80m", "wind_speed_120m",
                 "relative_humidity_2m", "surface_pressure"}
model_features = set(st.session_state["features"])
missing = model_features - LIVE_FEATURES

if missing:
    st.error(f"""Ce modèle utilise des features non disponibles en direct via Open-Meteo :
{', '.join(sorted(missing)[:8])}{'...' if len(missing) > 8 else ''}

Le monitoring live n'est possible que pour un modèle entraîné exclusivement sur
des variables météo qu'Open-Meteo fournit.""")
    st.stop()

st.caption("⚠️ Vitesse à 100m approximée par interpolation 80m/120m")
lat = st.number_input("Latitude", value=9.3)
lon = st.number_input("Longitude", value=105.8)

if st.button("🔄 Rafraîchir la prédiction"):
    window = st.session_state["results"]["window"]
    recent = fetch_live_wind(lat, lon, hours_needed=window + 1)
    pred = predict_next_hour(
        st.session_state["results"]["model"],
        st.session_state["results"]["scaler_X"],
        st.session_state["results"]["scaler_y"],
        recent, st.session_state["features"], window)

    hist = st.session_state.get("live_history", [])
    hist.append({"time": recent["time"].iloc[-1],
                 "actual": recent["wind_speed_100m_approx"].iloc[-1],
                 "predicted": pred})
    st.session_state["live_history"] = hist

hist = st.session_state.get("live_history", [])
if hist:
    fig = go.Figure()
    fig.add_scatter(x=[h["time"] for h in hist], y=[h["actual"] for h in hist], name="Observé (approx. 100m)")
    fig.add_scatter(x=[h["time"] for h in hist], y=[h["predicted"] for h in hist], name="Prédit (h+1)")
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Dernière prédiction", f"{hist[-1]['predicted']:.2f} m/s")