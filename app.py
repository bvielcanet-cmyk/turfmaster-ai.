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
    .num-badge { background-color: #34495e; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 10px; }
    .podium-badge { background-color: #f1c40f; color: #000; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; float: right; }
    .prediction-line { color: #e67e22; font-weight: bold; font-size: 14px; margin-top: 5px; border-top: 1px solid #eee; padding-top: 5px; }
    .value-text { color: #28a745; font-weight: bold; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE IA AFFINÉE ---

def calculer_ia_precision(cote, capital, discipline, fraction=0.20):
    base_adv = {"Trot 🐎": 1.08, "Galop/Plat 🏇": 1.12, "Obstacle/Haies 🪵": 1.15}
    avantage = base_adv.get(discipline, 1.10)
    
    # Correction de Volatilité
    correction = 1 - (math.log(cote) / 50) 
    avantage_ajuste = avantage * correction
    
    prob_ia = (1 / cote) * avantage_ajuste
    val = prob_ia * cote
    
    # Indice Podium
    indice_podium = min(98, int((prob_ia ** 0.7) * 100 * 2.2))
    
    # Gestion des mises (Kelly Safefuard)
    mise = 0
    if val > 1.03:
        f_kelly = (prob_ia * (cote - 1) - (1 - prob_ia)) / (cote - 1)
        mise = max(0, capital * f_kelly * fraction)
        mise = min(mise, capital * 0.05) # Max 5% du capital
    
    # --- NOUVELLE LOGIQUE DE PRÉVISION INTELLIGENTE ---
    if cote <= 2.5:
        if val > 1.07: prev = "🔥 Grand Favori IA (Vise la gagne)"
        else: prev = "⭐ Favori Logique (Top 3 Probable)"
    elif 2.5 < cote <= 8.0:
        if val > 1.15: prev = "📈 Bel Outsider (Value Podium)"
        else: prev = "📊 Chance régulière (Top 5)"
    else:
        if val > 1.20: prev = "💎 Pépite Débusquée (Grosse Value)"
        else: prev = "🎲 Coup de poker (Outsider)"
        
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
            if nom != "INCONNU" and cote:
                partants.append({"num": num, "nom": nom, "cote": float(cote)})
        return pd.DataFrame(partants)
    except: return pd.DataFrame()

def extraire_texte(texte):
    blocs = re.split(r'\n(?=\d+\s*\n)', texte.strip())
    partants = []
    for bloc in blocs:
        lignes = [l.strip() for l in bloc.split('\n') if l.strip()]
        if len(lignes) >= 2:
            try:
                num = lignes[0]
                nom = lignes[1].upper()
                cote_matches = re.findall(r'(\d+[\.,]\d+)', bloc)
                if cote_matches:
                    cote = float(cote_matches[-1].replace(',', '.'))
                    partants.append({"num": num, "nom": nom, "cote": cote})
            except: continue
    return pd.DataFrame(partants)

# --- 4. INTERFACE ---

st.title("🏇 TurfMaster AI : Précision v3")

col_a, col_b = st.columns(2)
with col_a:
    capital = st.number_input("💰 Capital (€)", value=500)
with col_b:
    discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])

tab1, tab2, tab3 = st.tabs(["🔗 URL", "📝 TEXTE", "📊 BILAN"])

df_final = pd.DataFrame()

with tab1:
    url_in = st.text_input("Lien Zeturf :")
    if st.button("🚀 ANALYSE AUTO"): df_final = extraire_url(url_in)

with tab2:
    txt_in = st.text_area("Copier-coller Zeturf :", height=150)
    if st.button("🚀 ANALYSE TEXTE"): df_final = extraire_texte(txt_in)

with tab3:
    if st.session_state.historique:
        df_hist = pd.DataFrame(st.session_state.historique)
        st.metric("Profit Net", f"{round(df_hist['gain'].sum(), 2)} €")
        st.line_chart(df_hist['gain'].cumsum())
        if st.button("Réinitialiser"): st.session_state.historique = []; st.rerun()
    else: st.write("Aucun historique.")

# --- 5. RÉSULTATS ---

if not df_final.empty:
    resultats = []
    for _, row in df_final.iterrows():
        mise, val, podium, prev = calculer_ia_precision(row['cote'], capital, discipline)
        if podium >= 60:
            res = row.to_dict(); res.update({"mise": mise, "value": val, "podium": podium, "prev": prev})
            resultats.append(res)
    
    resultats = sorted(resultats, key=lambda x: x['podium'], reverse=True)
    
    for res in resultats:
        avantage_pct = round((res['value'] - 1) * 100, 1)
        st.markdown(f"""
        <div class="card">
            <span class="podium-badge">🏆 Podium : {res['podium']}%</span>
            <span class="num-badge">{res['num']}</span><b>{res['nom']}</b><br>
            <span class="value-text">+{avantage_pct}% d'avantage IA</span><br>
            Cote: <b>{res['cote']}</b> | Mise: <b style="color:#28a745;">{round(res['mise'], 2)}€</b>
            <div class="prediction-line">🎯 {res['prev']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        if c1.button(f"✅ GAGNÉ ({res['num']})"):
            st.session_state.historique.append({"gain": (res['mise'] * res['cote']) - res['mise']})
            st.rerun()
        if c2.button(f"❌ PERDU ({res['num']})"):
            st.session_state.historique.append({"gain": -res['mise']})
            st.rerun()
