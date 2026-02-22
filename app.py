import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import re
import math

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro (Cloud DB)", page_icon="🧠", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

# Connexion au Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

# Lecture des données existantes
def load_data():
    try:
        # On lit le sheet (la mise en cache est désactivée pour avoir le temps réel)
        return conn.read(ttl=0)
    except:
        return pd.DataFrame(columns=['date', 'discipline', 'hippodrome', 'num', 'resultat', 'avantage_ia'])

# Style CSS
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .card { background-color: white; border-radius: 15px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .text-black { color: #000000 !important; font-weight: bold; }
    .ia-status { background: #f0f2f6; padding: 10px; border-radius: 10px; color: #000; border-left: 5px solid #28a745; }
    .value-text { color: #28a745; font-weight: bold; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE D'APPRENTISSAGE ---

def obtenir_avantage_appris(df, discipline):
    if df.empty: return 1.12
    filtre = df[df['discipline'] == discipline].tail(20)
    if len(filtre) < 5: return 1.12
    reussite = pd.to_numeric(filtre['resultat']).mean()
    return 1.16 if reussite > 0.40 else 1.08 if reussite < 0.15 else 1.12

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Mémoire Cloud")
df_ia = load_data()

tab1, tab2 = st.tabs(["🚀 Analyse Course", "📊 Mémoire Google Sheets"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        capital = st.number_input("💰 Capital (€)", value=500)
        discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
    with col2:
        hippo_manuel = st.text_input("📍 Hippodrome", value="Paris-Vincennes")

    adv_dynamique = obtenir_avantage_appris(df_ia, discipline)
    st.markdown(f'<div class="ia-status">🤖 <b>Mémoire Cloud active</b> | Avantage : {adv_dynamique}</div>', unsafe_allow_html=True)

    txt_in = st.text_area("1. Collez les partants :", height=150)
    
    if st.button("🚀 ANALYSER"):
        # (Logique d'extraction identique aux versions précédentes...)
        # ... [Code d'analyse et affichage des cartes ici] ...
        st.info("Analyse terminée. Pour enregistrer l'arrivée, utilisez le champ ci-dessous.")

    # Bloc d'enregistrement vers Google Sheets
    st.markdown("---")
    arrivee_txt = st.text_input("🏁 Enregistrer l'arrivée (ex: 4-8-1) :")
    
    if st.button("💾 SAUVEGARDER DANS LE CLOUD"):
        if arrivee_txt and 'df_course' in st.session_state:
            nums_gagnants = re.findall(r'\b(\d{1,2})\b', arrivee_txt)[:3]
            
            # Préparation des nouvelles lignes
            nouvelles_lignes = []
            for _, r in st.session_state.df_course.iterrows():
                est_p = 1 if str(r['num']) in nums_gagnants else 0
                nouvelles_lignes.append({
                    'date': datetime.now(tz_paris).strftime("%Y-%m-%d %H:%M"),
                    'discipline': discipline,
                    'hippodrome': hippo_manuel,
                    'num': r['num'],
                    'resultat': est_p,
                    'avantage_ia': adv_dynamique
                })
            
            # Mise à jour du Google Sheet
            df_maj = pd.concat([df_ia, pd.DataFrame(nouvelles_lignes)], ignore_index=True)
            conn.update(data=df_maj)
            st.success("Données synchronisées avec Google Sheets !")
            st.rerun()

with tab2:
    st.header("📊 Données Google Sheets")
    if not df_ia.empty:
        st.checkbox("Afficher l'historique complet", key="show_hist")
        if st.session_state.show_hist:
            st.dataframe(df_ia.sort_index(ascending=False))
        
        # Petit résumé
        stats = df_ia.groupby('discipline')['resultat'].agg(['mean', 'count']).reset_index()
        st.table(stats)
    else:
        st.write("Aucune donnée dans le Cloud.")
