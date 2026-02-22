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
    .anomalie { color: #d9534f; font-weight: bold; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE IA OPTIMISÉE ---

def calculer_ia_precision(cote, capital, discipline, fraction=0.20):
    # 1. Avantages de base
    base_adv = {"Trot 🐎": 1.08, "Galop/Plat 🏇": 1.12, "Obstacle/Haies 🪵": 1.15}
    avantage = base_adv.get(discipline, 1.10)
    
    # 2. Correction de Volatilité (L'IA est plus méfiante si la cote est haute)
    # Plus la cote augmente, plus on réduit légèrement l'avantage
    correction = 1 - (math.log(cote) / 50) 
    avantage_ajuste = avantage * correction
    
    prob_ia = (1 / cote) * avantage_ajuste
    val = prob_ia * cote
    
    # 3. Indice Podium avec courbe de probabilité logarithmique
    indice_podium = min(98, int((prob_ia ** 0.7) * 100 * 2.2))
    
    # 4. Kelly Criterion "Safeguard"
    # On limite la mise max à 5% du capital par cheval pour la sécurité
    if val > 1.05:
        f_kelly = (prob_ia * (cote - 1) - (1 - prob_ia)) / (cote - 1)
        mise = max(0, capital * f_kelly * fraction)
        mise = min(mise, capital * 0.05) 
    else:
        mise = 0
        
    # Prévision d'ordre
    if val > 1.30: prev = "🔥 Grand Favori IA (1er)"
    elif val > 1.15: prev = "⭐ Podium Solide (Top 3)"
    else: prev = "📊 Outsider de Valeur (Top 5)"
    
    return mise, val, indice_podium, prev

# --- 3. EXTRACTION (Inchangée mais robuste) ---

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

st.title("🏇 TurfMaster AI : Précision Max")

col_a, col_b = st.columns(2)
with col_a:
    capital = st.number_input("💰 Capital total (€)", value=500)
with col_b:
    discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])

tab1, tab2, tab3 = st.tabs(["🔗 URL", "📝 TEXTE", "📊 PERFORMANCE"])

df_final = pd.DataFrame()

with tab1:
    url_in = st.text_input("Lien Zeturf :")
    if st.button("🚀 ANALYSE AUTO"): df_final = extraire_url(url_in)

with tab2:
    txt_in = st.text_area("Copier-coller Zeturf :", height=150)
    if st.button("🚀 ANALYSE MANUELLE"): df_final = extraire_texte(txt_in)

with tab3:
    if st.session_state.historique:
        df_hist = pd.DataFrame(st.session_state.historique)
        st.metric("Profit Net", f"{round(df_hist['gain'].sum(), 2)} €")
        st.line_chart(df_hist['gain'].cumsum())
    else: st.write("Aucun historique pour le moment.")

# --- 5. RESULTATS OPTIMISÉS ---

if not df_final.empty:
    resultats = []
    for _, row in df_final.iterrows():
        # Utilisation de la nouvelle logique de précision
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
            <span class="value-text">+{avantage_pct}% d'avantage IA</span>
            { '<br><span class="anomalie">⚠️ Attention : Value très élevée</span>' if avantage_pct > 50 else '' }
            <br>Cote: <b>{res['cote']}</b> | Mise: <b>{round(res['mise'], 2)}€</b>
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
