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

# Fichier de mémoire locale de l'IA
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
    .ia-status { background: #f0f2f6; padding: 10px; border-radius: 10px; font-size: 12px; border-left: 5px solid #28a745; margin-bottom: 15px; color: #000; }
    .pronostic-box { background-color: #ebf5fb; border-left: 5px solid #2980b9; padding: 10px; border-radius: 8px; margin-bottom: 20px; color: #000; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE D'APPRENTISSAGE ---

def obtenir_avantage_appris(discipline, hippodrome):
    try:
        df = pd.read_csv(DB_FILE)
        filtre = df[(df['discipline'] == discipline) | (df['hippodrome'] == hippodrome)].tail(15)
        if len(filtre) < 5: return 1.12
        reussite = filtre['resultat'].mean()
        if reussite > 0.40: return 1.16
        if reussite < 0.15: return 1.08
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

# --- 3. FONCTIONS D'EXTRACTION ---

def extraire_url_complete(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 13)'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
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

def extraire_texte_intelligent(texte):
    # Découpage par bloc commençant par un numéro seul sur sa ligne
    blocs = re.split(r'\n(?=\d+\s*\n)', texte.strip())
    partants = []
    for bloc in blocs:
        lignes = [l.strip() for l in bloc.split('\n') if l.strip()]
        if len(lignes) >= 2:
            try:
                num = lignes[0]
                nom = lignes[1].upper()
                # On cherche la musique (ligne avec chiffres + lettres p, a, m, h, s)
                musique = "Inconnue"
                for l in lignes:
                    if re.search(r'\d+[apmsh]', l.lower()): musique = l; break
                # On cherche la cote (dernier nombre décimal du bloc)
                cote_matches = re.findall(r'(\d+[\.,]\d+)', bloc)
                if cote_matches:
                    cote = float(cote_matches[-1].replace(',', '.'))
                    partants.append({"num": num, "nom": nom, "cote": cote, "musique": musique})
            except: continue
    return pd.DataFrame(partants)

# --- 4. INTERFACE ---

st.title("🧠 TurfMaster AI : Deep Learning")

col1, col2 = st.columns(2)
with col1:
    capital = st.number_input("💰 Capital (€)", value=500)
    discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
with col2:
    hippo_manuel = st.text_input("📍 Tag Hippodrome", value="Fontainebleau", help="Sert à l'apprentissage ciblé")

adv_dynamique = obtenir_avantage_appris(discipline, hippo_manuel)
st.markdown(f"""<div class="ia-status">🤖 <b>État de l'IA :</b> Mode {'Optimiste' if adv_dynamique > 1.12 else 'Prudent'}<br>
Avantage appliqué : <b>{adv_dynamique}</b> (Basé sur vos résultats à {hippo_manuel})</div>""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🔗 URL Zeturf", "📝 COPIER-COLLER", "📊 PERFORMANCE"])
df_final = pd.DataFrame()

with tab1:
    url_in = st.text_input("Lien de la course :")
    if st.button("🚀 ANALYSER URL"): df_final = extraire_url_complete(url_in)

with tab2:
    txt_in = st.text_area("Collez les partants ici :", height=200, placeholder="1\nGREEN GATE\n...\n10.4")
    if st.button("🚀 ANALYSER COPIER-COLLER"): df_final = extraire_texte_intelligent(txt_in)

with tab3:
    try:
        hist = pd.read_csv(DB_FILE)
        if not hist.empty:
            st.metric("Taux de réussite réel", f"{int(hist['resultat'].mean()*100)}%")
            st.write("Historique d'apprentissage :")
            st.dataframe(hist.tail(20))
            if st.button("Réinitialiser l'IA"): 
                os.remove(DB_FILE); initialiser_ia(); st.rerun()
        else: st.info("L'IA n'a pas encore de données.")
    except: st.write("Aucune donnée.")

# --- 5. CALCULS & RÉSULTATS ---

if not df_final.empty:
    hippo_final = df_final['hippo'].iloc[0] if 'hippo' in df_final.columns else hippo_manuel
    
    resultats = []
    for _, row in df_final.iterrows():
        # Calcul de probabilité avec avantage dynamique appris
        prob_ia = (1 / row['cote']) * adv_dynamique
        val = prob_ia * row['cote']
        podium = min(98, int((prob_ia ** 0.7) * 100 * 2.2))
        
        # Kelly Criterion limité à 5% du capital
        f_kelly = (prob_ia * (row['cote'] - 1) - (1 - prob_ia)) / (row['cote'] - 1)
        mise = min(max(0, capital * f_kelly * 0.20), capital * 0.05)
        
        # Libellé intelligent selon la cote
        if row['cote'] <= 2.5: prev = "🔥 Grand Favori (Gagne)" if val > 1.07 else "⭐ Favori (Top 3)"
        elif 2.5 < row['cote'] <= 8.0: prev = "📈 Bel Outsider (Podium)" if val > 1.15 else "📊 Chance (Top 5)"
        else: prev = "💎 Pépite Débusquée" if val > 1.20 else "🎲 Coup de poker"
        
        resultats.append({**row, "mise": mise, "value": val, "podium": podium, "prev": prev})

    resultats = sorted(resultats, key=lambda x: x['podium'], reverse=True)

    # BLOC TOP 5 ESTIMÉ
    st.markdown(f"""<div class="pronostic-box"><b>🏁 TOP 5 ESTIMÉ À {hippo_final.upper()} :</b><br>
    <span style="font-size: 20px;">{" - ".join([f"**{r['num']}**" for r in resultats[:5]])}</span></div>""", unsafe_allow_html=True)

    for i, res in enumerate(resultats):
        if res['podium'] >= 60 or i < 5:
            card_class = "card" if res['podium'] >= 60 else "card-low"
            avantage_pct = round((res['value'] - 1) * 100, 1)
            
            st.markdown(f"""
            <div class="{card_class}">
                <span class="podium-badge">🏆 Podium : {res['podium']}%</span>
                <span class="num-badge">{res['num']}</span>
                <span class="text-black" style="font-size:18px;">{res['nom']}</span><br>
                <small>🎵 {res['musique']}</small><br>
                <span class="text-black">Cote: {res['cote']}</span> | 
                Mise : <b style="color:#28a745;">{round(res['mise'], 2)}€</b><br>
                <span style="color:#28a745; font-size:12px;">+{avantage_pct}% d'avantage IA</span>
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
