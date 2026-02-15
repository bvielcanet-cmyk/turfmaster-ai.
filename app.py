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

# Tes identifiants directs
DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

# Design mobile
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .card { background-color: white; border-radius: 15px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS ---

def envoyer_telegram(message):
    token = st.secrets.get("TELEGRAM_TOKEN", DIRECT_TOKEN)
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID", DIRECT_CHAT_ID)
    url_tg = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        res = requests.post(url_tg, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
        return res.status_code == 200
    except: return False

def extraire_donnees(url):
    # User-Agent aléatoire pour éviter d'être bloqué
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Mobile Safari/537.36'}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code != 200:
            st.error(f"Erreur de connexion au site (Code {res.status_code})")
            return pd.DataFrame()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        partants = []

        # --- NOUVELLE MÉTHODE : Recherche par mots-clés ---
        # On cherche toutes les lignes de tableau
        lignes = soup.find_all('tr')
        
        for ligne in lignes:
            texte = ligne.get_text(separator="|").strip()
            # On cherche des lignes qui contiennent un chiffre (la cote) et du texte (le nom)
            # On cherche spécifiquement la classe 'runner' ou les spans de noms
            nom_elem = ligne.find(class_=re.compile("runner-name|name", re.I))
            cote_elem = ligne.find(class_=re.compile("cote-live|odds|cote", re.I))

            if nom_elem and cote_elem:
                try:
                    nom = nom_elem.get_text().strip()
                    cote_txt = cote_elem.get_text().strip().replace(',', '.')
                    # Extraction du premier nombre trouvé dans la cote
                    cote_match = re.search(r"[-+]?\d*\.\d+|\d+", cote_txt)
                    if cote_match:
                        cote = float(cote_match.group())
                        if cote > 1.0:
                            partants.append({"nom": nom, "cote": cote})
                except:
                    continue

        return pd.DataFrame(partants).drop_duplicates(subset=['nom'])
    except Exception as e:
        st.error(f"Erreur technique : {e}")
        return pd.DataFrame()

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI Pro")
st.info(f"🕒 Heure : {datetime.now(tz_paris).strftime('%H:%M:%S')}")

if st.button("🔔 TEST TELEGRAM"):
    if envoyer_telegram("✅ Test réussi !"): st.success("Reçu sur Telegram ?")
    else: st.error("Échec envoi.")

urls_input = st.text_area("Colle l'URL Zeturf ici :")
capital = st.number_input("Capital (€)", value=500)

if st.button("⚡ ANALYSER"):
    if urls_input:
        url = urls_input.strip().split('\n')[0] # On prend la 1ère pour le test
        with st.spinner("Lecture de la page..."):
            df = extraire_donnees(url)
            
            if not df.empty:
                st.success(f"✅ {len(df)} chevaux détectés")
                for _, row in df.iterrows():
                    # Calcul simplifié pour test
                    prob_ia = (1 / row['cote']) * 1.12
                    val = prob_ia * row['cote']
                    
                    if val > 1.05:
                        mise = max(0, capital * ((prob_ia * (row['cote']-1) - (1-prob_ia)) / (row['cote']-1)) * 0.25)
                        st.markdown(f"""<div class="card"><b>{row['nom']}</b><br>Cote: {row['cote']} | Value: {val:.2f}<br>Mise: {mise:.2f}€</div>""", unsafe_allow_html=True)
                        if val >= 1.10:
                            envoyer_telegram(f"💎 *VALUE*\n🐎 {row['nom']}\n📈 Cote: {row['cote']}\n💰 Mise: {round(mise, 2)}€")
            else:
                st.error("❌ Échec : Zeturf bloque peut-être l'accès ou l'URL est mauvaise.")
                st.info("Conseil : Vérifie que l'URL ressemble à : https://www.zeturf.fr/fr/course/2024-05-20/R1C1-vincennes-prix-de-la-republique")
    else:
        st.warning("Colle une URL.")
