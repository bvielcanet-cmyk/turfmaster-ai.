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

# Fichier de mémoire de l'IA
DB_FILE = "ia_memory.csv"

def initialiser_ia():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=['date', 'discipline', 'hippodrome', 'cote', 'resultat', 'avantage_ia'])
        df.to_csv(DB_FILE, index=False)

initialiser_ia()

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .card { background-color: white; border-radius: 15px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .card-low { background-color: #fafafa; border-radius: 15px; padding: 15px; border: 1px dashed #ccc; margin-bottom: 10px; opacity: 0.8; }
    .num-badge { background-color: #34495e; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 10px; }
    .podium-badge { background-color: #f1c40f; color: #000; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; float: right; }
    .text-black { color: #000000 !important; font-weight: bold; }
    .prediction-line { color: #e67e22; font-weight: bold; font-size: 14px; margin-top: 5px; border-top: 1px solid #eee; padding-top: 5px; }
    .ia-status { background: #f0f2f6; padding: 10px; border-radius: 10px; font-size: 12px; border-left: 5px solid #28a745; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE D'APPRENTISSAGE ---

def obtenir_avantage_appris(discipline, hippodrome):
    """L'IA analyse ses erreurs passées pour ajuster l'avantage actuel"""
    try:
        df = pd.read_csv(DB_FILE)
        # On regarde les 15 derniers paris sur cet hippodrome ou cette discipline
        filtre = df[(df['discipline'] == discipline) | (df['hippodrome'] == hippodrome)].tail(15)
        
        if len(filtre) < 5: return 1.12 # Base si pas assez de données
        
        reussite = filtre['resultat'].mean()
        if reussite > 0.40: return 1.16 # L'IA est en feu, elle augmente sa confiance
        if reussite < 0.15: return 1.08 # L'IA se trompe souvent, elle devient prudente
        return 1.12
    except: return 1.12

def enregistrer_pari(discipline, hippodrome, cote, resultat, avantage):
    df = pd.read_csv(DB_FILE)
    nouveau = pd.DataFrame([{
        'date': datetime.now(tz_paris).strftime("%Y-%m-%d"),
        'discipline': discipline,
        'hippodrome': hippodrome,
        'cote': cote,
        'resultat': 1 if resultat == "GAGNÉ" else 0,
        'avantage_ia': avantage
    }])
    df = pd.concat([df, nouveau], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

# --- 3. EXTRACTION ---

def extraire_url_complete(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 13)'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Extraction du nom de l'hippodrome (Tag)
        hippo = "Inconnu"
        header = soup.find('div', class_='course-header-info')
        if header: hippo = header.text.split('-')[0].strip()

        partants = []
        for ligne in soup.select('tr.runner-row'):
            num = ligne.find('span', class_='runner-number').text.strip() if ligne.find('span', class_='runner-number') else "?"
            nom = ligne.find('span', class_='runner-name').text.strip().upper() if ligne.find('span', class_='runner-name') else "INCONNU"
            cote_el = ligne.find('span', class_='cote-live')
            cote = "".join(c for c in cote_el.text if c.isdigit() or c in [',', '.']).replace(',', '.') if cote_el else ""
            musique_el = ligne.find('span', class_='musique')
            musique = musique_el.text.strip() if musique_el else "Inconnue"
            if nom != "INCONNU" and cote:
                partants.append({"num": num, "nom": nom, "cote": float(cote), "musique": musique, "hippo": hippo})
        return pd.DataFrame(partants)
    except: return pd.DataFrame()

# --- 4. INTERFACE ---

st.title("🧠 TurfMaster AI : Deep Learning")

col1, col2 = st.columns(2)
with col1:
    capital = st.number_input("💰 Capital (€)", value=500)
    discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
with col2:
    hippo_manuel = st.text_input("📍 Hippodrome (Tag)", placeholder="ex: Vincennes")

# État de l'IA
adv_dynamique = obtenir_avantage_appris(discipline, hippo_manuel)
st.markdown(f"""<div class="ia-status">🤖 <b>État de l'IA :</b> Mode {'Optimiste' if adv_dynamique > 1.12 else 'Prudent'}<br>
Avantage calculé : <b>{adv_dynamique}</b> (basé sur l'historique {hippo_manuel})</div>""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🔗 URL", "📊 PERFORMANCE"])

df_final = pd.DataFrame()

with tab1:
    url_in = st.text_input("Lien Zeturf :")
    if st.button("🚀 ANALYSE"): df_final = extraire_url_complete(url_in)

with tab2:
    try:
        hist = pd.read_csv(DB_FILE)
        if not hist.empty:
            st.write("Derniers paris analysés :")
            st.dataframe(hist.tail(10))
            st.metric("Taux de réussite global", f"{int(hist['resultat'].mean()*100)}%")
        else: st.info("L'IA n'a pas encore de souvenirs.")
    except: st.write("Aucune donnée.")

# --- 5. CALCULS & AFFICHAGE ---

if not df_final.empty:
    hippo_final = df_final['hippo'].iloc[0] if 'hippo' in df_final.columns else hippo_manuel
    
    resultats = []
    for _, row in df_final.iterrows():
        # Logique IA avec avantage dynamique
        prob_ia = (1 / row['cote']) * adv_dynamique
        val = prob_ia * row['cote']
        podium = min(98, int((prob_ia ** 0.7) * 100 * 2.2))
        
        # Kelly
        f_kelly = (prob_ia * (row['cote'] - 1) - (1 - prob_ia)) / (row['cote'] - 1)
        mise = min(max(0, capital * f_kelly * 0.20), capital * 0.05)
        
        prev = "🔥 Favori" if row['cote'] < 3 else "📈 Outsider"
        
        resultats.append({**row, "mise": mise, "value": val, "podium": podium, "prev": prev})

    resultats = sorted(resultats, key=lambda x: x['podium'], reverse=True)

    st.subheader(f"📍 Course à {hippo_final}")
    
    for i, res in enumerate(resultats):
        if res['podium'] >= 60 or i < 5:
            card_class = "card" if res['podium'] >= 60 else "card-low"
            st.markdown(f"""
            <div class="{card_class}">
                <span class="podium-badge">🏆 {res['podium']}%</span>
                <span class="num-badge">{res['num']}</span><span class="text-black">{res['nom']}</span><br>
                <small>🎵 {res['musique']}</small><br>
                <b>Mise : {round(res['mise'], 2)}€</b> | Cote : <span class="text-black">{res['cote']}</span>
                <div class="prediction-line">🎯 {res['prev']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button(f"✅ GAGNÉ ({res['num']})"):
                enregistrer_pari(discipline, hippo_final, res['cote'], "GAGNÉ", adv_dynamique)
                st.rerun()
            if c2.button(f"❌ PERDU ({res['num']})"):
                enregistrer_pari(discipline, hippo_final, res['cote'], "PERDU", adv_dynamique)
                st.rerun()
