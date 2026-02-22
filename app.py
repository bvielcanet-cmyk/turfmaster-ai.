import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .card { background-color: white; border-radius: 15px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .value-box { background-color: #f0fff4; border-radius: 8px; padding: 10px; margin: 10px 0; border: 1px dashed #28a745; }
    .value-text { color: #28a745; font-weight: bold; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE D'EXTRACTION ---

def extraire_donnees_url(url):
    """Scraper mobile-emulation"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile',
        'Accept-Language': 'fr-FR,fr;q=0.9',
        'Referer': 'https://www.google.com/'
    }
    try:
        session = requests.Session()
        res = session.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        partants = []
        # Recherche large des lignes de chevaux
        lignes = soup.find_all(['tr', 'div'], class_=lambda x: x and ('runner' in x or 'row' in x))
        for ligne in lignes:
            nom_elem = ligne.find(['span', 'div', 'td'], class_=lambda x: x and ('name' in x or 'runner' in x))
            cote_elem = ligne.find(['span', 'div', 'td'], class_=lambda x: x and ('cote' in x or 'odds' in x))
            if nom_elem and cote_elem:
                nom = nom_elem.text.strip()
                cote = "".join(c for c in cote_elem.text if c.isdigit() or c in [',', '.']).replace(',', '.')
                if nom and cote:
                    try: partants.append({"nom": nom, "cote": float(cote)})
                    except: continue
        return pd.DataFrame(partants).drop_duplicates(subset=['nom'])
    except: return pd.DataFrame()

def extraire_donnees_texte(texte):
    """Extrait les chevaux et cotes à partir d'un copier-coller brut du site"""
    # Cherche un nom suivi d'une cote (ex: "Eclair de lune ... 5.2")
    pattern = r"([A-Z][A-Z\s]+)\s+.*?\s+(\d+[\.,]\d+)"
    matches = re.findall(pattern, texte)
    partants = [{"nom": m[0].strip(), "cote": float(m[1].replace(',', '.'))} for m in matches]
    return pd.DataFrame(partants).drop_duplicates(subset=['nom'])

def calculer_kelly(cote, capital, discipline, fraction=0.25):
    avantages = {"Trot 🐎": 1.10, "Galop/Plat 🏇": 1.14, "Obstacle/Haies 🪵": 1.18}
    avantage_ia = avantages.get(discipline, 1.12)
    prob_reelle = (1 / cote) * avantage_ia
    val = prob_reelle * cote
    if val <= 1.05: return 0, val
    kelly = (prob_reelle * (cote - 1) - (1 - prob_reelle)) / (cote - 1)
    return max(0, capital * kelly * fraction), val

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI Pro")

discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
capital = st.number_input("💰 Mon Capital (€)", value=500)

tab1, tab2 = st.tabs(["🔗 Par URL (Auto)", "📝 Par Texte (Manuel)"])

with tab1:
    url_input = st.text_input("Colle l'URL Zeturf ici :")
    btn_url = st.button("🚀 ANALYSER URL")

with tab2:
    txt_input = st.text_area("Colle le texte de la page ici (si l'URL est bloquée) :", height=150)
    btn_txt = st.button("🚀 ANALYSER TEXTE")

# --- 4. EXECUTION ---

def afficher_resultats(df):
    if df.empty:
        st.error("Aucune donnée trouvée. Vérifiez la source.")
        return
    
    st.success(f"{len(df)} chevaux détectés")
    for _, row in df.iterrows():
        mise, val = calculer_kelly(row['cote'], capital, discipline)
        if val > 1.05:
            avantage_pct = round((val - 1) * 100, 1)
            confiance = min(100, int((val - 1) * 400))
            st.markdown(f"""
            <div class="card">
                <b style="font-size: 18px;">🐎 {row['nom']}</b>
                <div class="value-box">
                    <small>AVANTAGE IA</small><br><span class="value-text">+{avantage_pct}%</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>Cote : <b>{row['cote']}</b></span>
                    <span>Mise : <b style="color:#28a745;">{round(mise, 2)}€</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(confiance / 100)
            
            # Telegram
            token = st.secrets.get("TELEGRAM_TOKEN")
            chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
            if token and chat_id:
                msg = f"🏇 {row['nom']} | +{avantage_pct}% | Mise: {round(mise, 2)}€"
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": msg})

if btn_url and url_input:
    afficher_resultats(extraire_donnees_url(url_input))

if btn_txt and txt_input:
    afficher_resultats(extraire_donnees_texte(txt_input))
