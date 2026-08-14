import streamlit as st
import plotly.express as px
import pandas as pd
from src.splitting import causal_split

st.title("3. Split causal en 5 zones")

if "df_ext" not in st.session_state:
    st.warning("Génère d'abord les features à l'étape 2.")
    st.stop()

df_ext = st.session_state["df_ext"]

col1, col2, col3, col4 = st.columns(4)
p_gtr = col1.slider("GRU train %", 50, 80, 65) / 100
p_ges = col2.slider("GRU early-stop %", 5, 15, 10) / 100
p_xtr = col3.slider("XGB train %", 5, 15, 10) / 100
p_xes = col4.slider("XGB early-stop %", 3, 10, 7) / 100

if p_gtr + p_ges + p_xtr + p_xes >= 0.97:
    st.error("La somme des 4 zones dépasse 97% — il ne reste plus assez de test final. Réduis une zone.")
    st.stop()

zones, bounds = causal_split(df_ext, p_gtr, p_ges, p_xtr, p_xes)
st.session_state["zones"] = zones

rows = [{"Zone": name, "Début": b[0], "Fin": b[1]} for name, b in bounds.items()]
fig = px.timeline(pd.DataFrame(rows), x_start="Début", x_end="Fin", y="Zone", color="Zone")
fig.update_yaxes(autorange="reversed")
st.plotly_chart(fig, use_container_width=True)

for name, d in zones.items():
    st.caption(f"**{name}** : {len(d):,} lignes")
st.success("Split enregistré — passe à l'étape 4 (Training).")