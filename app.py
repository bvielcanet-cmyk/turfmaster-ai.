import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

# Tes identifiants en dur
DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

# Design mobile
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .card { background-color: white; border-radius: 15px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS AMÉLIORÉES ---

def envoyer_telegram(message):
    token = st.secrets.get("TELEGRAM_TOKEN", DIRECT_TOKEN)
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID", DIRECT_CHAT_ID)
    url_tg = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        res = requests.post(url_tg, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
        if res.status_code != 200:
            st.error(f"❌ Erreur Telegram : {res.text}")
            return False
        return True
    except Exception as e:
        st.error(f"❌ Erreur Connexion : {e}")
        return False

def extraire_donnees(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Extraction de l'heure plus flexible
        heure_c = "00h00"
        header = soup.find('div', class_='course-header-info')
        if header and '-' in header.text:
            heure_c = header.text.split('-')[1].strip()

        partants = []
        # On cherche toutes les lignes qui ressemblent à un partant
        lignes = soup.find_all('tr', class_=lambda x: x and 'runner' in x.lower())
        
        for ligne in lignes:
            try:
                nom = ligne.find('span', class_='runner-name').text.strip()
                cote_elem = ligne.find('span', class_='cote-live')
                if not cote_elem: # fallback si la classe change
                    cote_elem = ligne.find('span', class_='cote')
                
                cote = cote_elem.text.strip().replace(',', '.')
                partants.append({"nom": nom, "cote": float(cote), "heure": heure_c})
            except:
                continue
        
        return pd.DataFrame(partants)
    except Exception as e:
        st.error(f"Erreur Scraper : {e}")
        return pd.DataFrame()

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI Pro")
st.info(f"🕒 Heure Paris : {datetime.now(tz_paris).strftime('%H:%M:%S')}")

# Bouton de Test
if st.button("🔔 TESTER TELEGRAM"):
    envoyer_telegram("✅ Test de connexion TurfMaster")

st.divider()

urls_input = st.text_area("URLs Zeturf (une par ligne) :")
capital = st.number_input("Capital (€)", value=500)

if st.button("⚡ LANCER L'ANALYSE"):
    if urls_input:
        links = urls_input.strip().split('\n')
        for url in links:
            url = url.strip()
            if not url: continue
            
            st.write(f"Analyse de : {url}...")
            df = extraire_donnees(url)
            
            if not df.empty:
                st.success(f"✅ {len(df)} chevaux trouvés !")
                for _, row in df.iterrows():
                    prob = (1 / row['cote']) * 1.12
                    val = prob * row['cote']
                    
                    if val > 1.05:
                        mise = max(0, capital * ((prob * (row['cote']-1) - (1-prob)) / (row['cote']-1)) * 0.25)
                        st.markdown(f"""<div class="card"><b>{row['nom']}</b> | Cote: {row['cote']} | <b>Value: {val:.2f}</b><br>Mise : {mise:.2f}€</div>""", unsafe_allow_html=True)
                        if val >= 1.10:
                            envoyer_telegram(f"🏇 *VALUE*\n🐎 {row['nom']}\n📈 Cote: {row['cote']}\n💰 Mise: {round(mise, 2)}€")
            else:
                st.warning("Désolé, aucun cheval trouvé sur cette page. Vérifie l'URL.")
    else:
        st.warning("Veuillez coller une URL.")
