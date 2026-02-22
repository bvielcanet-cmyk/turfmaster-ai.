import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .card { background-color: white; border-radius: 15px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .num-badge { background-color: #34495e; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 10px; }
    .value-box { background-color: #f0fff4; border-radius: 8px; padding: 10px; margin: 10px 0; border: 1px dashed #28a745; }
    .podium-badge { background-color: #f1c40f; color: #000; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; float: right; }
    .value-text { color: #28a745; font-weight: bold; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE IA ---

def calculer_analyse_ia(cote, capital, discipline, fraction=0.25):
    avantages = {"Trot 🐎": 1.10, "Galop/Plat 🏇": 1.14, "Obstacle/Haies 🪵": 1.18}
    avantage_ia = avantages.get(discipline, 1.12)
    
    # Probabilité estimée par l'IA
    prob_ia = (1 / cote) * avantage_ia
    val = prob_ia * cote
    
    # Estimation de placement (Probabilité de finir dans les 3 premiers)
    # Formule simplifiée : La probabilité de gagner + une marge de sécurité pour le podium
    indice_podium = min(95, int(prob_ia * 2.5 * 100)) 
    
    kelly = (prob_ia * (cote - 1) - (1 - prob_ia)) / (cote - 1)
    mise = max(0, capital * kelly * fraction)
    
    return mise, val, indice_podium

# --- 3. EXTRACTION ---

def extraire_donnees_url(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Heure de la course
        heure_c = "N/A"
        header = soup.find('div', class_='course-header-info')
        if header and '-' in header.text:
            heure_c = header.text.split('-')[1].strip()

        partants = []
        for ligne in soup.select('tr.runner-row'):
            num = ligne.find('span', class_='runner-number').text.strip() if ligne.find('span', class_='runner-number') else "?"
            nom = ligne.find('span', class_='runner-name').text.strip() if ligne.find('span', class_='runner-name') else "Inconnu"
            cote_elem = ligne.find('span', class_='cote-live')
            cote_txt = "".join(c for c in cote_elem.text if c.isdigit() or c in [',', '.']).replace(',', '.') if cote_elem else ""
            
            if nom != "Inconnu" and cote_txt:
                try: partants.append({"num": num, "nom": nom, "cote": float(cote_txt), "heure": heure_c})
                except: continue
        return pd.DataFrame(partants)
    except: return pd.DataFrame()

# --- 4. INTERFACE ---

st.title("🏇 TurfMaster AI : Pronostics")

discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
capital = st.number_input("💰 Capital (€)", value=500)
url_input = st.text_input("🔗 URL Zeturf :")

if st.button("⚡ ANALYSER ET CLASSER"):
    if url_input:
        df = extraire_donnees_url(url_input)
        
        if not df.empty:
            # Calculer l'IA pour chaque cheval
            resultats = []
            for _, row in df.iterrows():
                mise, val, podium = calculer_analyse_ia(row['cote'], capital, discipline)
                if val > 1.05:
                    res = row.to_dict()
                    res.update({"mise": mise, "value": val, "podium": podium})
                    resultats.append(res)
            
            # TRI PAR INDICE DE PODIUM (Les meilleurs en premier)
            resultats = sorted(resultats, key=lambda x: x['podium'], reverse=True)
            
            if resultats:
                st.success(f"Top {len(resultats)} des meilleures opportunités détectées :")
                for res in resultats:
                    avantage_pct = round((res['value'] - 1) * 100, 1)
                    
                    st.markdown(f"""
                    <div class="card">
                        <span class="podium-badge">🏆 Indice Podium : {res['podium']}%</span>
                        <div>
                            <span class="num-badge">{res['num']}</span>
                            <b style="font-size: 18px;">{res['nom']}</b>
                        </div>
                        <div class="value-box">
                            <small>AVANTAGE DÉTECTÉ</small><br>
                            <span class="value-text">+{avantage_pct}%</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>Cote : <b>{res['cote']}</b></span>
                            <span style="font-size: 18px;">Mise : <b style="color:#28a745;">{round(res['mise'], 2)}€</b></span>
                        </div>
                        <small style="color: #7f8c8d;">🕗 Départ estimé : {res['heure']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Aucune opportunité rentable détectée sur cette course.")
        else:
            st.error("Erreur de lecture. Vérifiez le lien.")
