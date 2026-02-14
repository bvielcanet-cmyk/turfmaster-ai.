import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import logging
import json
from pathlib import Path

# --- CONFIGURATION SYSTÈME ---
logging.basicConfig(level=logging.INFO)
tz_paris = pytz.timezone('Europe/Paris')

st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")

# --- DESIGN MOBILE (CSS) ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; font-size: 18px; border: none; }
    .card { background-color: white; border-radius: 15px; padding: 20px; border: 1px solid #eee; margin-bottom: 15px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .badge { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; color: white; float: right; }
    .stNumberInput input { font-size: 18px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS LOGIQUES ---

def temps_restant(heure_course):
    """Calcule les minutes restantes avant le départ (Heure de Paris)"""
    try:
        maintenant = datetime.now(tz_paris)
        heure_str = heure_course.lower().replace('h', ':').strip()
        h, m = map(int, heure_str.split(':'))
        depart = maintenant.replace(hour=h, minute=m, second=0, microsecond=0)
        diff = depart - maintenant
        return int(diff.total_seconds() / 60)
    except: return None

def extraire_donnees(url):
    """Scraper Zeturf robuste pour mobile"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Date et Heure de la course
        header = soup.find('div', class_='course-header-info')
        info_temps = header.text.strip() if header else "Aujourd'hui - 00h00"
        parts = info_temps.split('-')
        date_c = parts[0].strip()
        heure_c = parts[1].strip() if len(parts) > 1 else "00h00"

        partants = []
        # On cherche les lignes de partants (sélecteurs standards Zeturf)
        for ligne in soup.select('tr.runner-row'):
            nom = ligne.find('span', class_='runner-name').text.strip()
            cote_raw = ligne.find('span', class_='cote-live').text.strip().replace(',', '.')
            if cote_raw:
                partants.append({"nom": nom, "cote": float(cote_raw), "date": date_c, "heure": heure_c})
        return pd.DataFrame(partants)
    except: return pd.DataFrame()

def calculer_kelly(cote, capital, avantage=1.10, fraction=0.25):
    """Calcule la mise optimale via Kelly pondéré"""
    prob_reelle = (1 / cote) * avantage
    if prob_reelle * cote <= 1: return 0, prob_reelle
    kelly = (prob_reelle * (cote - 1) - (1 - prob_reelle)) / (cote - 1)
    return max(0, capital * kelly * fraction), prob_reelle

# --- INTERFACE UTILISATEUR ---

st.title("🏇 TurfMaster AI Pro")
heure_actuelle = datetime.now(tz_paris).strftime("%H:%M:%S")
st.info(f"🕒 Heure de Paris : **{heure_actuelle}**")

# 1. Analyseur de Course
url_course = st.text_input("🔗 Lien Zeturf de la course :", placeholder="https://www.zeturf.fr/...")
capital = st.number_input("💰 Ton Capital (€)", value=500, min_value=10)

if url_course:
    with st.spinner('Analyse des cotes en direct...'):
        df = extraire_donnees(url_course)
        
        if not df.empty:
            st.subheader(f"🎯 Pronostics - {df['date'].iloc[0]}")
            for _, row in df.iterrows():
                mise, prob = calculer_kelly(row['cote'], capital)
                indice_value = prob * row['cote']
                mins = temps_restant(row['heure'])
                
                # Gestion des couleurs du badge temps
                if mins is None: b_col, b_txt = "#666", "Heure ?"
                elif mins <= 0: b_col, b_txt = "#000", "🏁 Parti"
                elif mins < 10: b_col, b_txt = "#d9534f", f"🔥 {mins} min"
                elif mins < 30: b_col, b_txt = "#f0ad4e", f"⏳ {mins} min"
                else: b_col, b_txt = "#5cb85c", f"✅ {mins} min"

                # Affichage des opportunités (Value > 1.05)
                if indice_value > 1.05:
                    st.markdown(f"""
                    <div class="card">
                        <span class="badge" style="background-color: {b_col};">{b_txt}</span>
                        <b style="font-size: 20px; color: #1a1a1a;">{row['nom']}</b><br>
                        <div style="margin-top: 15px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <small style="color: #666;">COTE</small><br><b style="font-size: 18px;">{row['cote']}</b>
                            </div>
                            <div>
                                <small style="color: #666;">VALUE</small><br><b style="font-size: 18px; color: #28a745;">{indice_value:.2f}</b>
                            </div>
                            <div style="text-align: right;">
                                <small style="color: #666;">MISE</small><br><b style="font-size: 22px; color: #28a745;">{mise:.2f}€</b>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Aucune donnée trouvée. Vérifie l'URL ou la connexion.")

# 2. Section Bilan
st.divider()
st.subheader("📊 Bilan & Bankroll")

if 'log' not in st.session_state: st.session_state.log = []

with st.expander("📝 Enregistrer un pari"):
    with st.form("pari_form"):
        f_nom = st.text_input("Cheval")
        f_mise = st.number_input("Mise (€)", value=10.0)
        f_cote = st.number_input("Cote", value=2.0)
        f_res = st.radio("Résultat", ["Gagné ✅", "Perdu ❌"], horizontal=True)
        if st.form_submit_button("Sauvegarder"):
            profit = (f_mise * f_cote - f_mise) if "Gagné" in f_res else -f_mise
            st.session_state.log.append({"nom": f_nom, "gain": profit})
            st.success(f"Bilan mis à jour : {profit:+.2f}€")

if st.session_state.log:
    df_res = pd.DataFrame(st.session_state.log)
    st.metric("Profit Total", f"{df_res['gain'].sum():+.2f} €")
    st.dataframe(df_res, use_container_width=True)

