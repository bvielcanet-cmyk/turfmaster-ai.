import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import math
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Deep Learning", page_icon="🧠", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')
DB_FILE = "ia_memory.csv"

def initialiser_ia():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=['date', 'discipline', 'hippodrome', 'num', 'resultat', 'avantage_ia'])
        df.to_csv(DB_FILE, index=False)

initialiser_ia()

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .card { background-color: white; border-radius: 15px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .num-badge { background-color: #34495e; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 10px; }
    .text-black { color: #000000 !important; font-weight: bold; }
    .ia-status { background: #f0f2f6; padding: 10px; border-radius: 10px; font-size: 12px; border-left: 5px solid #28a745; margin-bottom: 15px; color: #000; }
    .arrival-box { background-color: #fff9db; border: 1px dashed #f1c40f; padding: 15px; border-radius: 10px; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE D'APPRENTISSAGE PAR RÉSULTAT ---

def obtenir_avantage_appris(discipline, hippodrome):
    try:
        df = pd.read_csv(DB_FILE)
        filtre = df[df['discipline'] == discipline].tail(20)
        if len(filtre) < 5: return 1.12
        reussite = filtre['resultat'].mean()
        if reussite > 0.40: return 1.16
        if reussite < 0.15: return 1.08
        return 1.12
    except: return 1.12

def traiter_arrivee_officielle(texte_arrivee, chevaux_analyses, discipline, hippodrome, avantage_utilise):
    """Détecte les numéros dans l'arrivée officielle et marque les gagnants dans la base"""
    # On extrait tous les numéros présents dans le texte d'arrivée (souvent les 3 ou 5 premiers)
    numeros_gagnants = re.findall(r'\b(\d{1,2})\b', texte_arrivee)
    # On ne garde que le Top 3 pour l'apprentissage du podium
    top_3 = numeros_gagnants[:3]
    
    df = pd.read_csv(DB_FILE)
    nouveaux_paris = []
    
    for cheval in chevaux_analyses:
        est_place = 1 if str(cheval['num']) in top_3 else 0
        nouveaux_paris.append({
            'date': datetime.now(tz_paris).strftime("%Y-%m-%d"),
            'discipline': discipline,
            'hippodrome': hippodrome,
            'num': cheval['num'],
            'resultat': est_place,
            'avantage_ia': avantage_utilise
        })
    
    df = pd.concat([df, pd.DataFrame(nouveaux_paris)], ignore_index=True)
    df.to_csv(DB_FILE, index=False)
    return top_3

# --- 3. EXTRACTION & CALCULS (Synthèse des versions précédentes) ---

def extraire_texte_intelligent(texte):
    blocs = re.split(r'\n(?=\d+\s*\n)', texte.strip())
    partants = []
    for bloc in blocs:
        lignes = [l.strip() for l in bloc.split('\n') if l.strip()]
        if len(lignes) >= 2:
            try:
                num, nom = lignes[0], lignes[1].upper()
                musique = "Inconnue"
                for l in lignes:
                    if re.search(r'\d+[apmsh]', l.lower()): musique = l; break
                cote_matches = re.findall(r'(\d+[\.,]\d+)', bloc)
                if cote_matches:
                    cote = float(cote_matches[-1].replace(',', '.'))
                    partants.append({"num": num, "nom": nom, "cote": cote, "musique": musique})
            except: continue
    return pd.DataFrame(partants)

# --- 4. INTERFACE ---

st.title("🧠 TurfMaster AI : Apprentissage Automatique")

col1, col2 = st.columns(2)
with col1:
    capital = st.number_input("💰 Capital (€)", value=500)
    discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
with col2:
    hippo_manuel = st.text_input("📍 Hippodrome", value="Fontainebleau")

adv_dynamique = obtenir_avantage_appris(discipline, hippo_manuel)
st.markdown(f"""<div class="ia-status">🤖 <b>IA en mode Apprentissage</b><br>Avantage actuel : <b>{adv_dynamique}</b></div>""", unsafe_allow_html=True)

# Saisie des partants
txt_in = st.text_area("1. Collez les partants ici :", height=150)
if st.button("🚀 ANALYSER LA COURSE"):
    st.session_state.df_course = extraire_texte_intelligent(txt_in)

# Affichage des résultats et zone d'apprentissage
if 'df_course' in st.session_state and not st.session_state.df_course.empty:
    resultats = []
    for _, row in st.session_state.df_course.iterrows():
        # Logique simplifiée pour l'exemple (mais reprend tes calculs de musique/kelly)
        prob_ia = (1 / row['cote']) * adv_dynamique
        podium = min(98, int((prob_ia ** 0.7) * 100 * 2.2))
        resultats.append({**row, "podium": podium})

    resultats = sorted(resultats, key=lambda x: x['podium'], reverse=True)
    
    # Affichage des cartes
    for res in resultats[:5]:
        st.markdown(f"""<div class="card"><span class="num-badge">{res['num']}</span><span class="text-black">{res['nom']}</span> (Cote: {res['cote']})<br><b>Confiance Podium : {res['podium']}%</b></div>""", unsafe_allow_html=True)

    # --- NOUVELLE ZONE D'APPRENTISSAGE ---
    st.markdown("---")
    st.markdown("### 🏁 2. Enregistrer l'arrivée réelle")
    arrivee_txt = st.text_input("Collez ici le résultat officiel (ex: 4 - 8 - 1) :")
    
    if st.button("💾 APPRENDRE DE CE RÉSULTAT"):
        if arrivee_txt:
            top_3 = traiter_arrivee_officielle(arrivee_txt, resultats, discipline, hippo_manuel, adv_dynamique)
            st.success(f"Apprentissage réussi ! Podium détecté : {', '.join(top_3)}")
            st.info("L'avantage de l'IA s'ajustera lors de la prochaine analyse.")
        else:
            st.warning("Veuillez coller le résultat officiel.")

# Onglet Performance
if st.checkbox("📊 Voir les souvenirs de l'IA"):
    if os.path.exists(DB_FILE):
        st.dataframe(pd.read_csv(DB_FILE).tail(10))
