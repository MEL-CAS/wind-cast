# ══ pages/1_Import.py — MIS À JOUR (garde le mode CSV existant + ajoute le mode localisation) ══
import streamlit as st
import pandas as pd
from src.agent import analyze_dataset
from src.opendata import geocode_location, download_wind_dataset, diagnose_and_clean

st.title("1. Import du dataset")

mode = st.radio("Source des données", ["📍 Localisation (vent, via Open-Meteo)", "📄 Fichier CSV"], horizontal=True)

# ══════════════════════════════════════════════════════════════
# MODE LOCALISATION — nouveau
# ══════════════════════════════════════════════════════════════
if mode.startswith("📍"):
    place = st.text_input("Nom du lieu (ville, site...)", placeholder="ex. Ouessant, France")

    if st.button("🔍 Rechercher") and place:
        candidates = geocode_location(place)
        if not candidates:
            st.error(f"Aucun lieu trouvé pour « {place} ». Essaie un nom plus précis (ex. avec le pays).")
        else:
            st.session_state["geo_candidates"] = candidates

    if "geo_candidates" in st.session_state:
        candidates = st.session_state["geo_candidates"]
        options = [f"{c['name']}, {c.get('admin1','')}, {c['country']} "
                   f"({c['latitude']:.3f}, {c['longitude']:.3f})" for c in candidates]
        choice = st.selectbox("Confirme le lieu exact", options)
        selected = candidates[options.index(choice)]

        col1, col2 = st.columns(2)
        start_date = col1.date_input("Date de début", value=pd.Timestamp("2015-01-01"))
        end_date = col2.date_input("Date de fin", value=pd.Timestamp.today())

        if st.button("⬇️ Télécharger et préparer le dataset"):
            with st.spinner(f"Téléchargement Open-Meteo pour {selected['name']}..."):
                df_raw = download_wind_dataset(
                    selected["latitude"], selected["longitude"],
                    str(start_date), str(end_date))

            with st.spinner("Diagnostic et nettoyage..."):
                try:
                    df_clean, fixes, warnings = diagnose_and_clean(
                        df_raw, datetime_col="time", target_col="ma_cible",
                        secondary_col="variable_secondaire", temperature_col="temperature",
                        pressure_col="pression", precipitation_col="precipitation",
                        direction_col="direction")
                except ValueError as e:
                    st.error(str(e))
                    st.stop()

            st.success(f"✅ {len(df_clean):,} lignes prêtes — {selected['name']}, {selected['country']}")
            if fixes:
                st.info("Corrections appliquées :\n" + "\n".join(f"- {f}" for f in fixes))
            if warnings:
                st.warning("À vérifier :\n" + "\n".join(f"- {w}" for w in warnings))

            st.dataframe(df_clean.head(10))

            # Mapping déterministe — connu à l'avance, pas besoin de l'agent ici
            st.session_state["raw_df"] = df_clean
            st.session_state["config"] = {
                "datetime_col": "time",
                "target_col": "ma_cible",
                "feature_cols": ["variable_secondaire", "temperature", "pression",
                                  "precipitation", "direction"],
            }
            st.success("Dataset prêt — passe à l'étape 2 (Features) dans le menu à gauche.")

# ══════════════════════════════════════════════════════════════
# MODE FICHIER CSV — inchangé, agent maison à 6 règles
# ══════════════════════════════════════════════════════════════
else:
    uploaded = st.file_uploader("Dépose ton fichier CSV", type="csv")

    if uploaded:
        df = pd.read_csv(uploaded)
        st.session_state["raw_df"] = df
        st.subheader("Aperçu")
        st.dataframe(df.head(10))
        st.caption(f"{df.shape[0]:,} lignes · {df.shape[1]} colonnes")

        if st.button("🔍 Analyser avec l'agent"):
            with st.spinner("Analyse des colonnes par les 6 règles..."):
                report = analyze_dataset(df)
            st.session_state["agent_report"] = report

        if "agent_report" in st.session_state:
            report = st.session_state["agent_report"]
            st.subheader("Décisions de l'agent (traçables)")
            for rule in report["rules_fired"]:
                (st.warning if rule.startswith("⚠") else st.info)(rule)

            st.subheader("Valide ou corrige le mapping")
            cols = df.columns.tolist()
            def safe_index(v): return cols.index(v) if v in cols else 0

            datetime_col = st.selectbox("Colonne datetime", cols, index=safe_index(report["datetime_column"]))
            target_col = st.selectbox("Colonne cible", cols, index=safe_index(report["target_column"]))
            feature_cols = st.multiselect("Colonnes features", cols, default=report["feature_columns"])

            if st.button("✅ Confirmer ce mapping"):
                st.session_state["config"] = {
                    "datetime_col": datetime_col, "target_col": target_col, "feature_cols": feature_cols,
                }
                st.success("Mapping confirmé — passe à l'étape 2 (Features) dans le menu à gauche.")