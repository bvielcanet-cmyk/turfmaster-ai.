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
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🧠", layout="centered")
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
    .text-black-small { color: #000000 !important; font-size: 14px; font-weight: 500; }
    .ia-status { background: #f0f2f6; padding: 10px; border-radius: 10px; font-size: 12px; border-left: 5px solid #28a745; margin-bottom: 15px; color: #000; }
    .pronostic-box { background-color: #ebf5fb; border-left: 5px solid #2980b9; padding: 10px; border-radius: 8px; margin-bottom: 20px; color: #000; }
    .value-text { color: #28a745; font-weight: bold; font-size: 16px; }
    .prediction-line { color: #e67e22; font-weight: bold; font-size: 13px; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE IA & APPRENTISSAGE ---

def analyser_musique(musique):
    if not musique or musique == "Inconnue": return 1.0
    score_forme = 1.0
    resultats = re.findall(r'(\d|D|A|T)', musique)[:4]
    for i, res in enumerate(resultats):
        poids = 1 / (i + 1)
        if res == '1': score_forme += 0.05 * poids
        elif res in ['2', '3']: score_forme += 0.03 * poids
        elif res in ['D', 'A', 'T']: score_forme -= 0.04 * poids
    return score_forme

def obtenir_avantage_appris(discipline):
    try:
        df = pd.read_csv(DB_FILE)
        filtre = df[df['discipline'] == discipline].tail(20)
        if len(filtre) < 5: return 1.12
        reussite = filtre['resultat'].mean()
        if reussite > 0.40: return 1.16
        if reussite < 0.15: return 1.08
        return 1.12
    except: return 1.12

# --- 3. EXTRACTION ---

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

st.title("🧠 TurfMaster AI Pro v5.1")

col1, col2 = st.columns(2)
with col1:
    capital = st.number_input("💰 Capital (€)", value=500)
    discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
with col2:
    hippo_manuel = st.text_input("📍 Hippodrome", value="Paris-Vincennes")

adv_dynamique = obtenir_avantage_appris(discipline)
st.markdown(f"""<div class="ia-status">🤖 <b>IA Mode :</b> {discipline} | <b>Avantage :</b> {adv_dynamique}</div>""", unsafe_allow_html=True)

txt_in = st.text_area("1. Collez les partants Zeturf :", height=150)
if st.button("🚀 LANCER L'ANALYSE"):
    st.session_state.df_course = extraire_texte_intelligent(txt_in)

if 'df_course' in st.session_state and not st.session_state.df_course.empty:
    resultats = []
    for _, row in st.session_state.df_course.iterrows():
        # Calculs de précision avec musique
        boost_m = analyser_musique(row['musique'])
        correction_v = 1 - (math.log(row['cote']) / 50) 
        prob_ia = (1 / row['cote']) * adv_dynamique * boost_m * correction_v
        
        val = prob_ia * row['cote']
        podium = min(98, int((prob_ia ** 0.7) * 100 * 2.2))
        
        # Kelly Criterion
        f_kelly = (prob_ia * (row['cote'] - 1) - (1 - prob_ia)) / (row['cote'] - 1)
        mise = min(max(0, capital * f_kelly * 0.20), capital * 0.05)
        
        # Libellé intelligent
        if row['cote'] <= 2.5: prev = "🔥 Grand Favori IA" if val > 1.07 else "⭐ Favori Logique"
        elif 2.5 < row['cote'] <= 8.0: prev = "📈 Bel Outsider" if val > 1.15 else "📊 Chance régulière"
        else: prev = "💎 Pépite Débusquée" if val > 1.20 else "🎲 Coup de poker"

        resultats.append({**row, "podium": podium, "mise": mise, "value": val, "prev": prev})

    resultats = sorted(resultats, key=lambda x: x['podium'], reverse=True)
    
    # TOP 5 ESTIMÉ
    st.markdown(f"""<div class="pronostic-box"><b>🏁 ORDRE D'ARRIVÉE ESTIMÉ :</b><br>
    <span style="font-size: 20px;">{" - ".join([f"**{r['num']}**" for r in resultats[:5]])}</span></div>""", unsafe_allow_html=True)

    # CARTES
    for i, res in enumerate(resultats):
        if res['podium'] >= 60 or i < 5:
            card_alpha = 1.0 if res['podium'] >= 60 else 0.75
            st.markdown(f"""
            <div class="card" style="opacity: {card_alpha};">
                <span class="num-badge">{res['num']}</span><span class="text-black" style="font-size:18px;">{res['nom']}</span><br>
                <span class="text-black-small">🎵 {res['musique']} | Cote : {res['cote']}</span><br>
                <span class="text-black" style="font-size:16px;">Confiance Podium : {res['podium']}%</span><br>
                <span class="value-text">Mise : {round(res['mise'], 2)}€</span>
                <div class="prediction-line">🎯 {res['prev']}</div>
            </div>
            """, unsafe_allow_html=True)

    # APPRENTISSAGE
    st.markdown("---")
    arrivee_txt = st.text_input("🏁 2. Collez l'arrivée officielle pour apprendre :")
    if st.button("💾 ENREGISTRER ET APPRENDRE"):
        if arrivee_txt:
            nums_gagnants = re.findall(r'\b(\d{1,2})\b', arrivee_txt)[:3]
            df_m = pd.read_csv(DB_FILE)
            for r in resultats:
                est_p = 1 if str(r['num']) in nums_gagnants else 0
                df_m = pd.concat([df_m, pd.DataFrame([{
                    'date': datetime.now(tz_paris).strftime("%Y-%m-%d"),
                    'discipline': discipline, 'hippodrome': hippo_manuel,
                    'num': r['num'], 'resultat': est_p, 'avantage_ia': adv_dynamique
                }])], ignore_index=True)
            df_m.to_csv(DB_FILE, index=False)
            st.success(f"Apprentissage terminé (Top 3 : {', '.join(nums_gagnants)})")
            st.rerun()
