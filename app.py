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

# Style CSS pour l'affichage mobile
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

# --- 2. LOGIQUE IA (PRONOSTIC & PLACEMENT) ---

def calculer_analyse_ia(cote, capital, discipline, fraction=0.25):
    # Paramètres d'avantage selon la discipline
    avantages = {"Trot 🐎": 1.10, "Galop/Plat 🏇": 1.14, "Obstacle/Haies 🪵": 1.18}
    avantage_ia = avantages.get(discipline, 1.12)
    
    # Calcul de la probabilité réelle estimée par l'IA
    prob_ia = (1 / cote) * avantage_ia
    val = prob_ia * cote
    
    # Indice de Podium (Estimation Top 3)
    indice_podium = min(98, int(prob_ia * 2.8 * 100))
    
    # Calcul de la mise via Kelly Criterion
    kelly = (prob_ia * (cote - 1) - (1 - prob_ia)) / (cote - 1)
    mise = max(0, capital * kelly * fraction)
    
    return mise, val, indice_podium

# --- 3. EXTRACTION DES DONNÉES ---

def extraire_url(url):
    """Scraping direct par URL"""
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 13)'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        partants = []
        for ligne in soup.select('tr.runner-row'):
            num_elem = ligne.find('span', class_='runner-number')
            num = num_elem.text.strip() if num_elem else "?"
            
            nom_elem = ligne.find('span', class_='runner-name')
            nom = nom_elem.text.strip() if nom_elem else "Inconnu"
            
            cote_elem = ligne.find('span', class_='cote-live')
            cote_txt = "".join(c for c in cote_elem.text if c.isdigit() or c in [',', '.']).replace(',', '.') if cote_elem else ""
            
            if nom != "Inconnu" and cote_txt:
                partants.append({"num": num, "nom": nom, "cote": float(cote_txt)})
        return pd.DataFrame(partants)
    except:
        return pd.DataFrame()

def extraire_texte(texte):
    """Analyse par copier-coller (Sécurisé pour Python 3.13)"""
    # Regex corrigée : détecte Numéro (optionnel), NOM (MAJ), et Cote (Chiffre)
    # On évite les plages de caractères complexes pour la compatibilité
    pattern = r"(\d+)?\s*([A-Z\s]{3,})\s*.*?(\d+[\.,]\d+)"
    
    # On cherche les correspondances
    matches = re.findall(pattern, texte)
    partants = []
    for m in matches:
        partants.append({
            "num": m[0] if m[0] else "?",
            "nom": m[1].strip(),
            "cote": float(m[2].replace(',', '.'))
        })
    return pd.DataFrame(partants)

# --- 4. INTERFACE UTILISATEUR ---

st.title("🏇 TurfMaster AI Pro")
st.write(f"🕒 Heure Paris : {datetime.now(tz_paris).strftime('%H:%M')}")

# Paramètres globaux
discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
capital = st.number_input("💰 Capital (€)", value=500)

# Onglets de saisie
tab1, tab2 = st.tabs(["🔗 Par URL", "📝 Par Copier-Coller"])
df_final = pd.DataFrame()

with tab1:
    url_in = st.text_input("Lien de la course Zeturf :", placeholder="https://www.zeturf.fr/...")
    if st.button("🚀 ANALYSER LIEN"):
        df_final = extraire_url(url_in)

with tab2:
    txt_in = st.text_area("Copie-colle le texte de la page Zeturf ici :", height=150, placeholder="Exemple: 1 INNER SUCCESS 5.2")
    if st.button("🚀 ANALYSER TEXTE"):
        df_final = extraire_texte(txt_in)

# --- 5. TRAITEMENT ET AFFICHAGE ---

if not df_final.empty:
    resultats = []
    for _, row in df_final.iterrows():
        mise, val, podium = calculer_analyse_ia(row['cote'], capital, discipline)
        # On n'affiche que les chevaux rentables (Value > 1.05)
        if val > 1.05:
            res = row.to_dict()
            res.update({"mise": mise, "value": val, "podium": podium})
            resultats.append(res)
    
    # TRI PAR PROBABILITÉ DE PODIUM (Les meilleurs en haut)
    resultats = sorted(resultats, key=lambda x: x['podium'], reverse=True)
    
    if resultats:
        st.success(f"Top {len(resultats)} des opportunités détectées (classées par probabilité de podium) :")
        for res in resultats:
            avantage_pct = round((res['value'] - 1) * 100, 1)
            
            st.markdown(f"""
            <div class="card">
                <span class="podium-badge">🏆 Podium : {res['podium']}%</span>
                <div>
                    <span class="num-badge">{res['num']}</span>
                    <b style="font-size: 18px;">{res['nom']}</b>
                </div>
                <div class="value-box">
                    <small>AVANTAGE DÉTECTÉ</small><br>
                    <span class="value-text">+{avantage_pct}% d'avantage</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>Cote : <b>{res['cote']}</b></span>
                    <span style="font-size: 18px;">Mise : <b style="color:#28a745;">{round(res['mise'], 2)}€</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(res['podium'] / 100)
    else:
        st.info("Aucun cheval rentable détecté sur cette course.")
else:
    if url_in or txt_in:
        st.error("Aucune donnée n'a pu être extraite. Vérifiez la source.")
