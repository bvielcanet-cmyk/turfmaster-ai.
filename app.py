import streamlit as st
import pandas as pd
import re
import requests
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : Expert Synthèse", page_icon="🎯", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Configurez la clé API dans les Secrets.")
    st.stop()

# --- 2. FONCTIONS DE CALCUL & RECHERCHE ---

def extraire_data_expert(texte):
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

def analyse_synthese_ia(df, nom_hippo, discipline, capital):
    liste_chevaux = "\n".join([f"N°{row['num']} {row['nom']} ({row['fer']} | {row['musique']})" for _, row in df.iterrows()])
    
    # Prompt structuré pour une réponse claire et exploitable
    prompt = f"""Expert Turf 2026. Analyse Stratégique pour {nom_hippo} ({discipline}).
    
    DONNÉES :
    {liste_chevaux}

    MISSION : 
    1. Synthétise la météo et l'état de la piste pour {nom_hippo}.
    2. Établis l'ORDRE D'ARRIVÉE PROBABLE (Top 5).
    3. Détermine le TYPE DE PARI le plus rentable pour cette course (ex: Couplé Gagnant, Trio, Multi en 6).
    4. Calcule la MISE OPTIMALE selon la méthode Kelly pour un capital de {capital}€.

    FORMAT DE RÉPONSE OBLIGATOIRE (Clair & Concis) :
    ### 🌦️ MÉTÉO & TERRAIN
    (Ton analyse flash)
    
    ### 🏆 PRONOSTIC (Ordre d'arrivée)
    1er: N°X | 2ème: N°X | 3ème: N°X | 4ème: N°X | 5ème: N°X
    
    ### 🎫 TICKET STRATÉGIQUE (Max de gains)
    - **Pari conseillé** : [Type de pari]
    - **Combinaison** : [Numéros]
    - **Mise recommandée** : [X] €
    
    ### 💎 LE CONSEIL DE L'EXPERT
    (Une phrase sur l'outsider ou le piège à éviter)
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
    
    try:
        # Timeout étendu à 45s pour la synthèse
        response = requests.post(url, json=payload, timeout=45)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        return f"Erreur Google : {response.status_code}"
    except Exception as e:
        return f"Connexion interrompue. Réessayez l'analyse."

# --- 3. INTERFACE ---
st.title("🎯 TurfMaster 2.5 : Synthèse & Profit")
st.caption("Optimisation des gains via IA Gemini 2.5 Platinum")

if 'input_text' not in st.session_state:
    st.session_state['input_text'] = ""

with st.sidebar:
    st.header("⚙️ Configuration")
    nom_hippo = st.text_input("Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot", "Plat", "Obstacles"])
    st.divider()
    capital = st.number_input("Capital (€)", value=1000)
    if st.button("🧹 Vider les données"):
        st.session_state['input_text'] = ""
        st.rerun()

c1, c2 = st.columns([1, 1.2])

with c1:
    txt_in = st.text_area("📋 Partants (Num Nom Fer Musique) :", 
                          value=st.session_state['input_text'], 
                          height=350)
    st.session_state['input_text'] = txt_in
    
    if st.button("🚀 GÉNÉRER LE TICKET GAGNANT"):
        df = extraire_data_expert(txt_in)
        if not df.empty:
            with st.spinner(f"📡 Analyse et synthèse en cours pour {nom_hippo}..."):
                analyse = analyse_synthese_ia(df, nom_hippo, discipline, capital)
                with c2:
                    st.success("🏁 Analyse Terminée")
                    st.markdown(analyse)
        else:
            st.error("Aucune donnée détectée.")

with c2:
    if not 'analyse' in locals():
        st.info("Collez les partants. L'IA va définir l'ordre, le type de pari et la mise idéale pour maximiser vos gains.")

st.divider()
st.caption("Version 2.5 : Synthèse Augmentée & Gestion de Bankroll.")
