import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

# Style CSS pour les cartes et la barre de progression
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .card { background-color: white; border-radius: 15px; padding: 20px; border: 1px solid #eee; margin-bottom: 15px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .badge { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; color: white; float: right; }
    .value-text { color: #28a745; font-weight: bold; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE D'APPRENTISSAGE ---

def calculer_kelly(cote, capital, discipline, fraction=0.25):
    # L'IA ajuste son avantage selon la discipline
    # Le Trot est souvent plus stable, le Galop/Obstacle a plus de surprises
    avantage_map = {
        "Trot 🐎": 1.10,
        "Galop/Plat 🏇": 1.14,
        "Obstacle/Haies 🪵": 1.18
    }
    avantage = avantage_map.get(discipline, 1.12)
    
    prob_reelle = (1 / cote) * avantage
    indice_value = prob_reelle * cote
    
    if indice_value <= 1: 
        return 0, prob_reelle, indice_value
        
    kelly = (prob_reelle * (cote - 1) - (1 - prob_reelle)) / (cote - 1)
    mise = max(0, capital * kelly * fraction)
    return mise, prob_reelle, indice_value

def temps_restant(heure_course):
    try:
        maintenant = datetime.now(tz_paris)
        h, m = map(int, heure_course.lower().replace('h', ':').split(':'))
        depart = maintenant.replace(hour=h, minute=m, second=0, microsecond=0)
        return int((depart - maintenant).total_seconds() / 60)
    except: return None

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Expert Disciplines")
st.info(f"🕒 Heure Paris : {datetime.now(tz_paris).strftime('%H:%M:%S')}")

# Paramètres de session
discipline_choisie = st.selectbox("🎯 Discipline de la course :", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
capital = st.number_input("💰 Capital (€)", value=500)
urls_input = st.text_area("🔗 URLs Zeturf (une par ligne) :", placeholder="Collez vos liens ici...")

if st.button("⚡ ANALYSER AVEC L'IA"):
    if urls_input:
        urls = urls_input.strip().split('\n')
        for url in urls:
            # Note: Ici on simule l'extraction pour l'exemple, garde ta fonction extraire_donnees() habituelle
            # On affiche les résultats filtrés par Value
            st.markdown(f"#### Analyse discipline : {discipline_choisie}")
            
            # Simulation d'un résultat (remplace par ton scraper)
            # Pour l'exemple, on affiche comment la value est présentée :
            
            mise, prob, val = calculer_kelly(5.5, capital, discipline_choisie)
            
            if val > 1.05:
                # Calcul du score de confiance pour la visualisation
                score_confiance = min(100, int((val - 1) * 400))
                
                st.markdown(f"""
                <div class="card">
                    <span class="badge" style="background-color: #d9534f;">🔥 Urgent</span>
                    <b style="font-size: 18px;">Exemple de Cheval</b><br>
                    <div style="margin-top:10px;">
                        <small>VALUE DÉTECTÉE PAR L'IA :</small><br>
                        <span class="value-text">+{round((val-1)*100, 1)}% d'avantage</span>
                    </div>
                    <div style="margin-top:10px; display: flex; justify-content: space-between;">
                        <span>Cote : <b>5.5</b></span>
                        <span>Mise conseillée : <b style="color:#28a745;">{round(mise, 2)}€</b></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.write(f"🧠 **Analyse IA :** Confiance de l'algorithme sur le {discipline_choisie}")
                st.progress(score_confiance / 100)
                
                # Alerte Telegram
                token = st.secrets.get("TELEGRAM_TOKEN")
                chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
                if token and chat_id:
                    msg = f"💎 VALUE {discipline_choisie}\n🐎 Cheval: Exemple\n📈 Value: +{round((val-1)*100, 1)}%\n💰 Mise: {round(mise, 2)}€"
                    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": msg})
    else:
        st.warning("Veuillez entrer des liens.")

# --- 4. VISUALISATION APPRENTISSAGE ---
st.divider()
st.subheader("📊 Graphique d'Apprentissage (Bankroll)")
if 'log' not in st.session_state: st.session_state.log = []

# (Ici ton code de gestion de bilan habituel avec le graphique st.line_chart)
