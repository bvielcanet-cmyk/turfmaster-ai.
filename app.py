import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

# Identifiants de secours (les tiens)
DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

# Design mobile
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; font-size: 18px; }
    .card { background-color: white; border-radius: 15px; padding: 20px; border: 1px solid #eee; margin-bottom: 15px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .badge { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; color: white; float: right; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS ---

def envoyer_telegram(message):
    # On cherche d'abord dans les secrets, sinon on utilise tes codes directs
    token = st.secrets.get("TELEGRAM_TOKEN", DIRECT_TOKEN)
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID", DIRECT_CHAT_ID)
    
    url_tg = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        res = requests.post(url_tg, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
        return res.status_code == 200
    except:
        return False

def temps_restant(heure_course):
    try:
        maintenant = datetime.now(tz_paris)
        h, m = map(int, heure_course.lower().replace('h', ':').split(':'))
        depart = maintenant.replace(hour=h, minute=m, second=0, microsecond=0)
        diff = depart - maintenant
        return int(diff.total_seconds() / 60)
    except: return None

def extraire_donnees(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        header = soup.find('div', class_='course-header-info')
        heure_c = header.text.strip().split('-')[1].strip() if header else "00h00"
        partants = []
        for ligne in soup.select('tr.runner-row'):
            nom = ligne.find('span', class_='runner-name').text.strip()
            cote = ligne.find('span', class_='cote-live').text.strip().replace(',', '.')
            partants.append({"nom": nom, "cote": float(cote), "heure": heure_c})
        return pd.DataFrame(partants)
    except: return pd.DataFrame()

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI Pro")
st.info(f"🕒 Heure Paris : {datetime.now(tz_paris).strftime('%H:%M:%S')}")

# BOUTON DE TEST UNIQUE
if st.button("🔔 TESTER L'ENVOI TELEGRAM MAINTENANT"):
    with st.spinner("Envoi en cours..."):
        success = envoyer_telegram("✅ Connexion réussie ! Ton algorithme TurfMaster peut maintenant t'envoyer des alertes.")
        if success:
            st.success("Message envoyé ! Vérifie ton application Telegram.")
        else:
            st.error("L'envoi a échoué. Vérifie que tu as bien cliqué sur 'DÉMARRER' sur ton bot Telegram.")

st.divider()

urls_input = st.text_area("URLs Zeturf (une par ligne) :")
capital = st.number_input("Capital (€)", value=500)

if st.button("⚡ LANCER L'ANALYSE"):
    if urls_input:
        for url in urls_input.strip().split('\n'):
            df = extraire_donnees(url.strip())
            if not df.empty:
                st.markdown(f"### 🏁 Course : {url.split('/')[-2]}")
                for _, row in df.iterrows():
                    prob = (1 / row['cote']) * 1.12
                    val = prob * row['cote']
                    mise = max(0, capital * ((prob * (row['cote']-1) - (1-prob)) / (row['cote']-1)) * 0.25)
                    mins = temps_restant(row['heure'])
                    
                    if val > 1.05:
                        st.markdown(f"""<div class="card"><b>{row['nom']}</b> | Cote: {row['cote']} | Value: {val:.2f}<br>Mise : {mise:.2f}€</div>""", unsafe_allow_html=True)
                        if val >= 1.10:
                            envoyer_telegram(f"🏇 *VALUE*\n🐎 {row['nom']}\n📈 Cote: {row['cote']}\n💰 Mise: {round(mise, 2)}€")
    else:
        st.warning("Colle un lien Zeturf.")

# --- 4. BILAN ---
if 'log' not in st.session_state: st.session_state.log = []
with st.expander("📝 Enregistrer un pari"):
    with st.form("pari"):
        f_n, f_m, f_c = st.text_input("Nom"), st.number_input("Mise"), st.number_input("Cote")
        f_r = st.radio("Résultat", ["Gagné", "Perdu"])
        if st.form_submit_button("Ok"):
            g = (f_m * f_c - f_m) if f_r == "Gagné" else -f_m
            st.session_state.log.append({"nom": f_n, "gain": g})
