import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇")
tz_paris = pytz.timezone('Europe/Paris')

# --- 2. FONCTIONS LOGIQUES ---

def extraire_donnees(url):
    """Scraper réel pour extraire les partants de Zeturf"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Date et Heure
        header = soup.find('div', class_='course-header-info')
        info_temps = header.text.strip() if header else " - "
        heure_c = info_temps.split('-')[1].strip() if '-' in info_temps else "00h00"

        partants = []
        for ligne in soup.select('tr.runner-row'):
            nom = ligne.find('span', class_='runner-name').text.strip()
            cote_raw = ligne.find('span', class_='cote-live').text.strip().replace(',', '.')
            if cote_raw:
                partants.append({"nom": nom, "cote": float(cote_raw), "heure": heure_c})
        return pd.DataFrame(partants)
    except Exception as e:
        return pd.DataFrame()

def calculer_kelly(cote, capital, discipline, fraction=0.25):
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

discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
capital = st.number_input("💰 Mon Capital (€)", value=500)
urls_input = st.text_area("🔗 URLs Zeturf (une par ligne) :", height=120)

if st.button("⚡ ANALYSER LA JOURNÉE"):
    if urls_input:
        urls = urls_input.strip().split('\n')
        
        for url in urls:
            url = url.strip()
            if not url: continue
            
            # --- EXTRACTION RÉELLE ---
            df = extraire_donnees(url)
            
            if not df.empty:
                nom_course = url.split('/')[-2].replace('-', ' ').title()
                st.markdown(f"### 🏁 Course : {nom_course}")
                
                # On boucle sur CHAQUE CHEVAL trouvé par le scraper
                for _, row in df.iterrows():
                    mise, val = calculer_kelly(row['cote'], capital, discipline)
                    
                    # On affiche uniquement s'il y a une "Value"
                    if val > 1.05:
                        avantage_pct = round((val - 1) * 100, 1)
                        confiance = min(100, int((val - 1) * 400))
                        
                        # Affichage unique pour chaque cheval réel
                        with st.container():
                            st.markdown("---")
                            col_a, col_b = st.columns([2, 1])
                            
                            with col_a:
                                st.subheader(f"🐎 {row['nom']}")
                                st.write(f"**Avantage IA :** +{avantage_pct}%")
                                st.progress(confiance / 100)
                            
                            with col_b:
                                st.metric("MISE", f"{round(mise, 2)}€")
                                st.write(f"Cote : {row['cote']}")
                                st.write(f"Départ : {row['heure']}")

                        # ENVOI TELEGRAM
                        token = st.secrets.get("TELEGRAM_TOKEN")
                        chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
                        if token and chat_id:
                            msg = f"🏇 VALUE {discipline}\n📍 {nom_course}\n🐎 {row['nom']}\n📈 Adv: +{avantage_pct}%\n💰 Mise: {round(mise, 2)}€"
                            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                                          data={"chat_id": chat_id, "text": msg})
            else:
                st.error(f"Impossible de lire la course : {url}")
    else:
        st.warning("Veuillez coller des liens Zeturf.")

# --- 4. BILAN ---
st.divider()
st.subheader("📊 Suivi Bankroll")
if 'log' not in st.session_state: st.session_state.log = []
# (Graphique de bankroll ici)
