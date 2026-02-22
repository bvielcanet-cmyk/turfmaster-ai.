import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import math

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

if 'historique' not in st.session_state:
    st.session_state.historique = []

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .card { background-color: white; border-radius: 15px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .card-low { background-color: #fafafa; border-radius: 15px; padding: 15px; border: 1px dashed #ccc; margin-bottom: 10px; opacity: 0.8; }
    .num-badge { background-color: #34495e; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 10px; }
    .podium-badge { background-color: #f1c40f; color: #000; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; float: right; }
    .music-text { font-size: 12px; color: #666; font-style: italic; }
    .prediction-line { color: #e67e22; font-weight: bold; font-size: 14px; margin-top: 5px; border-top: 1px solid #eee; padding-top: 5px; }
    .text-black { color: #000000 !important; font-weight: bold; }
    .pronostic-box { background-color: #ebf5fb; border-left: 5px solid #2980b9; padding: 10px; border-radius: 8px; margin-bottom: 20px; color: #000; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE IA ---

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

def calculer_ia_precision(cote, capital, discipline, musique, fraction=0.20):
    base_adv = {"Trot 🐎": 1.08, "Galop/Plat 🏇": 1.12, "Obstacle/Haies 🪵": 1.15}
    boost_musique = analyser_musique(musique)
    avantage_final = base_adv.get(discipline, 1.10) * boost_musique
    
    correction = 1 - (math.log(cote) / 50) 
    avantage_ajuste = avantage_final * correction
    
    prob_ia = (1 / cote) * avantage_ajuste
    val = prob_ia * cote
    indice_podium = min(98, int((prob_ia ** 0.7) * 100 * 2.2))
    
    mise = 0
    if val > 1.03:
        f_kelly = (prob_ia * (cote - 1) - (1 - prob_ia)) / (cote - 1)
        mise = min(max(0, capital * f_kelly * fraction), capital * 0.05)
    
    if cote <= 2.5: prev = "🔥 Grand Favori IA" if val > 1.07 else "⭐ Favori Logique"
    elif 2.5 < cote <= 8.0: prev = "📈 Bel Outsider" if val > 1.15 else "📊 Chance régulière"
    else: prev = "💎 Pépite Débusquée" if val > 1.20 else "🎲 Coup de poker"
        
    return mise, val, indice_podium, prev

# --- 3. EXTRACTION ---

def extraire_url(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 13)'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        partants = []
        for ligne in soup.select('tr.runner-row'):
            num = ligne.find('span', class_='runner-number').text.strip() if ligne.find('span', class_='runner-number') else "?"
            nom = ligne.find('span', class_='runner-name').text.strip().upper() if ligne.find('span', class_='runner-name') else "INCONNU"
            cote_el = ligne.find('span', class_='cote-live')
            cote = "".join(c for c in cote_el.text if c.isdigit() or c in [',', '.']).replace(',', '.') if cote_el else ""
            musique_el = ligne.find('span', class_='musique')
            musique = musique_el.text.strip() if musique_el else "Inconnue"
            if nom != "INCONNU" and cote:
                partants.append({"num": num, "nom": nom, "cote": float(cote), "musique": musique})
        return pd.DataFrame(partants)
    except: return pd.DataFrame()

def extraire_texte(texte):
    blocs = re.split(r'\n(?=\d+\s*\n)', texte.strip())
    partants = []
    for bloc in blocs:
        lignes = [l.strip() for l in bloc.split('\n') if l.strip()]
        if len(lignes) >= 2:
            try:
                num, nom = lignes[0], lignes[1].upper()
                musique = "Inconnue"
                for l in lignes:
                    if re.search(r'\d+[apmsh]', l): musique = l; break
                cote_matches = re.findall(r'(\d+[\.,]\d+)', bloc)
                if cote_matches:
                    cote = float(cote_matches[-1].replace(',', '.'))
                    partants.append({"num": num, "nom": nom, "cote": cote, "musique": musique})
            except: continue
    return pd.DataFrame(partants)

# --- 4. INTERFACE ---

st.title("🏇 TurfMaster AI : Expert Top 5")

col_a, col_b = st.columns(2)
with col_a:
    capital = st.number_input("💰 Capital (€)", value=500)
with col_b:
    discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])

tab1, tab2 = st.tabs(["🔗 URL", "📝 TEXTE"])
df_final = pd.DataFrame()

with tab1:
    url_in = st.text_input("Lien Zeturf :")
    if st.button("🚀 ANALYSE AUTO"): df_final = extraire_url(url_in)

with tab2:
    txt_in = st.text_area("Copier-coller Zeturf :", height=150)
    if st.button("🚀 ANALYSE TEXTE"): df_final = extraire_texte(txt_in)

# --- 5. RÉSULTATS ---

if not df_final.empty:
    resultats = []
    for _, row in df_final.iterrows():
        mise, val, podium, prev = calculer_ia_precision(row['cote'], capital, discipline, row['musique'])
        res = row.to_dict(); res.update({"mise": mise, "value": val, "podium": podium, "prev": prev})
        resultats.append(res)
    
    # Tri global pour le Top 5
    resultats = sorted(resultats, key=lambda x: x['podium'], reverse=True)
    top_5 = resultats[:5]

    # TOP 5 ESTIMÉ
    st.markdown(f"""<div class="pronostic-box"><b>🏁 TOP 5 ESTIMÉ :</b><br>
    <span style="font-size: 20px;">{" - ".join([f"**{r['num']}**" for r in top_5])}</span></div>""", unsafe_allow_html=True)

    for i, res in enumerate(resultats):
        # On affiche si c'est une grosse probabilité OU si c'est dans le Top 5
        if res['podium'] >= 60 or i < 5:
            avantage_pct = round((res['value'] - 1) * 100, 1)
            # Style différent si sous les 60%
            card_style = "card" if res['podium'] >= 60 else "card-low"
            
            st.markdown(f"""
            <div class="{card_style}">
                <span class="podium-badge">🏆 Podium : {res['podium']}%</span>
                <span class="num-badge">{res['num']}</span><span class="text-black">{res['nom']}</span><br>
                <span class="music-text">🎵 {res['musique']}</span><br>
                <span class="value-text">+{avantage_pct}% d'avantage IA</span><br>
                <span class="text-black">Cote: {res['cote']}</span> | Mise: <b style="color:#28a745;">{round(res['mise'], 2)}€</b>
                <div class="prediction-line">🎯 {res['prev']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Boutons de suivi
            c1, c2 = st.columns(2)
            if c1.button(f"✅ GAGNÉ ({res['num']})"):
                st.session_state.historique.append({"gain": (res['mise'] * res['cote']) - res['mise']})
                st.rerun()
            if c2.button(f"❌ PERDU ({res['num']})"):
                st.session_state.historique.append({"gain": -res['mise']})
                st.rerun()
