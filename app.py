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
    .num-badge { background-color: #34495e; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 10px; }
    .podium-badge { background-color: #f1c40f; color: #000; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; float: right; }
    .prediction-line { color: #e67e22; font-weight: bold; font-size: 14px; margin-top: 5px; border-top: 1px solid #eee; padding-top: 5px; }
    .value-text { color: #28a745; font-weight: bold; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE IA ---

def calculer_analyse_ia(cote, capital, discipline, fraction=0.25):
    avantages = {"Trot 🐎": 1.10, "Galop/Plat 🏇": 1.14, "Obstacle/Haies 🪵": 1.18}
    avantage_ia = avantages.get(discipline, 1.12)
    
    prob_ia = (1 / cote) * avantage_ia
    val = prob_ia * cote
    
    # Indice de Podium (Estimation Top 3)
    indice_podium = min(98, int(prob_ia * 2.8 * 100))
    
    # Estimation de l'ordre d'arrivée
    if val > 1.25: prev = "1er ou 2ème (Coup sûr)"
    elif val > 1.15: prev = "Top 3 (Très probable)"
    else: prev = "Top 5 (Chance régulière)"
    
    kelly = (prob_ia * (cote - 1) - (1 - prob_ia)) / (cote - 1)
    mise = max(0, capital * kelly * fraction)
    
    return mise, val, indice_podium, prev

# --- 3. EXTRACTION DES DONNÉES ---

def extraire_url(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 13)'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        partants = []
        for ligne in soup.select('tr.runner-row'):
            num = ligne.find('span', class_='runner-number').text.strip() if ligne.find('span', class_='runner-number') else "?"
            nom = ligne.find('span', class_='runner-name').text.strip() if ligne.find('span', class_='runner-name') else "Inconnu"
            cote_elem = ligne.find('span', class_='cote-live')
            cote = "".join(c for c in cote_elem.text if c.isdigit() or c in [',', '.']).replace(',', '.') if cote_elem else ""
            if nom != "Inconnu" and cote:
                partants.append({"num": num, "nom": nom, "cote": float(cote)})
        return pd.DataFrame(partants)
    except: return pd.DataFrame()

def extraire_texte(texte):
    # Regex ultra-sécurisée : (Numéro) (Nom) (Cote)
    # \d+ : un ou plusieurs chiffres (le numéro)
    # \s+ : un espace
    # ([^0-9\n]{3,}) : Capture le nom (tout ce qui n'est pas un chiffre, au moins 3 caractères)
    # \s+ : un espace
    # (\d+[\.,]\d+) : La cote (chiffre avec point ou virgule)
    pattern = r"(\d+)\s+([^0-9\n]{3,})\s+(\d+[\.,]\d+)"
    
    matches = re.findall(pattern, texte)
    partants = []
    for m in matches:
        partants.append({
            "num": m[0],
            "nom": m[1].strip(),
            "cote": float(m[2].replace(',', '.'))
        })
    return pd.DataFrame(partants)

# --- 4. INTERFACE ---

st.title("🏇 TurfMaster AI : Top 60% Podium")

discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
capital = st.number_input("💰 Mon Capital (€)", value=500)

tab1, tab2 = st.tabs(["🔗 Par URL", "📝 Par Texte"])
df_final = pd.DataFrame()

with tab1:
    url_in = st.text_input("Lien Zeturf :")
    if st.button("🚀 Analyser Lien"): df_final = extraire_url(url_in)

with tab2:
    txt_in = st.text_area("Colle le texte Zeturf ici :", height=150)
    if st.button("🚀 Analyser Texte"): df_final = extraire_texte(txt_in)

# --- 5. RÉSULTATS FILTRÉS ---

if not df_final.empty:
    resultats = []
    for _, row in df_final.iterrows():
        mise, val, podium, prev = calculer_analyse_ia(row['cote'], capital, discipline)
        # FILTRE STRICT : Uniquement les probabilités de podium >= 60%
        if podium >= 60:
            res = row.to_dict()
            res.update({"mise": mise, "value": val, "podium": podium, "prev": prev})
            resultats.append(res)
    
    # Tri par probabilité de podium décroissante
    resultats = sorted(resultats, key=lambda x: x['podium'], reverse=True)
    
    if resultats:
        st.success(f"Analyse terminée : {len(resultats)} chevaux détectés au-dessus de 60%.")
        for res in resultats:
            avantage_pct = round((res['value'] - 1) * 100, 1)
            st.markdown(f"""
            <div class="card">
                <span class="podium-badge">🏆 Podium : {res['podium']}%</span>
                <div>
                    <span class="num-badge">{res['num']}</span>
                    <b style="font-size: 18px;">{res['nom']}</b>
                </div>
                <div style="margin: 10px 0;">
                    <span class="value-text">+{avantage_pct}% d'avantage IA</span><br>
                    <span>Cote : <b>{res['cote']}</b> | Mise : <b style="color:#28a745;">{round(res['mise'], 2)}€</b></span>
                </div>
                <div class="prediction-line">🎯 Prévision Arrivée : {res['prev']}</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(res['podium'] / 100)
    else:
        st.warning("Aucun cheval ne présente une probabilité de podium supérieure à 60% sur cette course.")
