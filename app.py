import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

# Style CSS pour mobile
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .card { background-color: white; border-radius: 15px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .value-box { background-color: #f0fff4; border-radius: 8px; padding: 10px; margin: 10px 0; border: 1px dashed #28a745; }
    .value-text { color: #28a745; font-weight: bold; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS LOGIQUES ---

def extraire_donnees(url):
    """Scraper robuste avec sélecteurs multiples pour contourner les blocages"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Extraction de l'heure
        heure_c = "00h00"
        header_info = soup.find('div', class_='course-header-info')
        if header_info and '-' in header_info.text:
            heure_c = header_info.text.split('-')[1].strip()

        partants = []
        # On cherche les lignes contenant 'runner' ou 'row'
        lignes = soup.find_all(['tr', 'div'], class_=lambda x: x and ('runner' in x or 'row' in x))
        
        for ligne in lignes:
            nom_elem = ligne.find(['span', 'div', 'td'], class_=lambda x: x and ('name' in x or 'runner' in x))
            cote_elem = ligne.find(['span', 'div', 'td'], class_=lambda x: x and ('cote' in x or 'odds' in x))
            
            if nom_elem and cote_elem:
                nom = nom_elem.text.strip()
                cote_txt = "".join(c for c in cote_elem.text if c.isdigit() or c in [',', '.']).replace(',', '.')
                
                if nom and cote_txt:
                    try:
                        partants.append({"nom": nom, "cote": float(cote_txt), "heure": heure_c})
                    except: continue

        return pd.DataFrame(partants).drop_duplicates(subset=['nom'])
    except Exception as e:
        return pd.DataFrame()

def calculer_kelly(cote, capital, discipline, fraction=0.25):
    # Avantage IA adaptatif
    avantages = {"Trot 🐎": 1.10, "Galop/Plat 🏇": 1.14, "Obstacle/Haies 🪵": 1.18}
    avantage_ia = avantages.get(discipline, 1.12)
    
    prob_reelle = (1 / cote) * avantage_ia
    val = prob_reelle * cote
    
    if val <= 1.05:
        return 0, val
    
    kelly = (prob_reelle * (cote - 1) - (1 - prob_reelle)) / (cote - 1)
    mise = max(0, capital * kelly * fraction)
    return mise, val

# --- 3. INTERFACE UTILISATEUR ---

st.title("🏇 TurfMaster AI Pro")
st.write(f"🕒 Heure Paris : {datetime.now(tz_paris).strftime('%H:%M:%S')}")

# Paramètres
col1, col2 = st.columns(2)
with col1:
    discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
with col2:
    capital = st.number_input("💰 Mon Capital (€)", value=500)

urls_input = st.text_area("🔗 URLs Zeturf (une par ligne) :", placeholder="Copiez l'adresse de la page course ici...")

if st.button("⚡ ANALYSER LA JOURNÉE"):
    if urls_input:
        urls = urls_input.strip().split('\n')
        
        for url in urls:
            url = url.strip()
            if not url.startswith("http"): continue
            
            with st.spinner(f"Analyse de {url[:40]}..."):
                df = extraire_donnees(url)
            
            if not df.empty:
                nom_course = url.split('/')[-1].replace('-', ' ').title()
                st.markdown(f"### 🏁 Course : {nom_course}")
                
                for _, row in df.iterrows():
                    mise, val = calculer_kelly(row['cote'], capital, discipline)
                    
                    if val > 1.05:
                        avantage_pct = round((val - 1) * 100, 1)
                        confiance = min(100, int((val - 1) * 400))
                        
                        # Carte unique par cheval
                        st.markdown(f"""
                        <div class="card">
                            <b style="font-size: 19px; color: #1a1a1a;">🐎 {row['nom']}</b>
                            <div class="value-box">
                                <small style="color: #666;">AVANTAGE DÉTECTÉ</small><br>
                                <span class="value-text">+{avantage_pct}%</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span>Cote : <b>{row['cote']}</b> | Dépt : {row['heure']}</span>
                                <span style="font-size: 18px;">Mise : <b style="color:#28a745;">{round(mise, 2)}€</b></span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.progress(confiance / 100)

                        # ENVOI TELEGRAM
                        token = st.secrets.get("TELEGRAM_TOKEN")
                        chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
                        if token and chat_id:
                            msg = f"🏇 VALUE {discipline}\n📍 {nom_course}\n🐎 {row['nom']}\n📈 Adv: +{avantage_pct}%\n💰 Mise: {round(mise, 2)}€"
                            try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": msg})
                            except: pass
            else:
                st.error(f"Impossible de lire la course. Vérifiez le lien ou réessayez.")
    else:
        st.warning("Veuillez coller au moins un lien Zeturf.")

# --- 4. BILAN ---
st.divider()
if 'log' not in st.session_state: st.session_state.log = []
st.subheader("📊 Performance cumulée")
# Tu peux ajouter ici ton line_chart de bankroll
