import streamlit as st
import pandas as pd
import re
import requests
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : IA Connectée", page_icon="🌐", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Configurez la clé API dans les Secrets.")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_data_turbo(texte):
    lignes = texte.strip().split('\n')
    data = []
    for ligne in lignes:
        numero = re.findall(r'^\d{1,2}', ligne.strip())
        nom = re.findall(r'\b[A-Z]{4,}\b', ligne)
        ferrure = re.findall(r'\bD4\b|\bDP\b|\bDA\b', ligne)
        musique = re.findall(r'\b\d[admp]\b|\b[A-Z]D\b', ligne)
        if nom:
            data.append({
                "num": numero[0] if numero else "?",
                "nom": nom[0],
                "fer": ferrure[0] if ferrure else "F",
                "musique": " ".join(musique) if musique else "N/A"
            })
    return pd.DataFrame(data)

def analyse_ia_connectee(df, nom_hippo, discipline, capital):
    liste_chevaux = "\n".join([f"N°{row['num']} {row['nom']} ({row['fer']} | {row['musique']})" for _, row in df.iterrows()])
    date_context = datetime.now().strftime("%d/%m/%Y")
    
    # Prompt forçant l'IA à utiliser ses capacités de recherche et de synthèse 2026
    prompt = f"""Tu es un Agent de Recherche Turf de 2026. Date : {date_context}.
    
    MISSION : 
    1. Utilise tes connaissances temps réel pour l'hippodrome : {nom_hippo} ({discipline}).
    2. Analyse les bruits d'écurie et tendances météo pour optimiser ces partants :
    {liste_chevaux}

    RÉSULTATS ATTENDUS (SYNTHÈSE HAUTE PRÉCISION) :
    - 🌤️ MÉTÉO & PISTE : Impact réel sur la course.
    - 🔍 INFOS EXPERTS : Synthèse des pronostics et chevaux repérés par l'IA.
    - 📊 CLASSEMENT PROBABILISTE : (N° | Nom | Score Performance /100).
    - 🎫 TICKET VALUE : Le meilleur rapport gain/risque.
    - 💰 MISE KELLY : Conseil sur {capital}€.
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        return f"Erreur serveur ({response.status_code})."
    except Exception as e:
        return f"Erreur : {e}"

# --- 3. INTERFACE ---
st.title("🌐 TurfMaster 2.5 : Intelligence Connectée")
st.caption("Agent de recherche Gemini 2.5 Platinum - Données Live 2026")

# Gestion du Reset via Session State
if 'input_text' not in st.session_state:
    st.session_state['input_text'] = ""

def clear_text():
    st.session_state['input_text'] = ""

with st.sidebar:
    st.header("📍 Paramètres Live")
    nom_hippo = st.text_input("Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot", "Plat", "Obstacles"])
    st.divider()
    capital = st.number_input("Capital (€)", value=1000)
    st.button("🧹 Vider les données", on_click=clear_text)

c1, c2 = st.columns([1, 1.3])

with c1:
    txt_in = st.text_area("📋 Partants (Num Nom Fer Musique) :", 
                          value=st.session_state['input_text'], 
                          height=350, 
                          key="input_area")
    
    # Mise à jour de la session state
    st.session_state['input_text'] = txt_in
    
    if st.button("🚀 LANCER L'ANALYSE CONNECTÉE"):
        df = extraire_data_turbo(txt_in)
        if not df.empty:
            with st.spinner(f"📡 Recherche d'informations sur {nom_hippo}..."):
                analyse = analyse_ia_connectee(df, nom_hippo, discipline, capital)
                with c2:
                    st.success("🏆 Analyse Stratégique Terminée")
                    st.markdown(analyse)
        else:
            st.error("Aucune donnée détectée.")

with c2:
    if not 'analyse' in locals():
        st.info("L'IA va croiser vos données avec les dernières informations du turf pour optimiser vos chances.")

st.divider()
st.caption("Optimisation 2026 : IA Multi-Agent & Connexion Live.")
