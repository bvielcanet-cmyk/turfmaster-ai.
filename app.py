import streamlit as st
import pandas as pd
import re
import requests
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : Anti-Timeout", page_icon="⚡", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente des Secrets.")
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

def analyse_ia_blindee(df, nom_hippo, discipline, capital):
    liste_chevaux = "\n".join([f"N°{row['num']} {row['nom']} ({row['fer']} | {row['musique']})" for _, row in df.iterrows()])
    
    # Prompt optimisé pour la vitesse de génération
    prompt = f"""Expert Turf 2026. Analyse Rapide.
    HIPPODROME : {nom_hippo} ({discipline})
    PARTANTS :
    {liste_chevaux}

    MISSION : 
    1. Synthèse météo/terrain locale pour {nom_hippo}.
    2. Liste des 3 favoris selon tes données live et bruits d'écurie.
    3. Classement Probabiliste (Num | Nom | Score /100).
    4. Mise Kelly sur {capital}€.
    Réponse concise et structurée.
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
    
    try:
        # Augmentation du timeout à 60 secondes pour éviter le 'Read timed out'
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"❌ Erreur Google ({response.status_code}) : {response.text}"
    except requests.exceptions.Timeout:
        return "⚠️ LE SERVEUR EST TROP LENT : La recherche d'infos prend plus de 60s. Réessayez dans un instant."
    except Exception as e:
        return f"❌ Erreur Réseau : {str(e)}"

# --- 3. INTERFACE ---
st.title("⚡ TurfMaster 2.5 : Version Haute Disponibilité")

# Gestion du Reset via Session State
if 'input_text' not in st.session_state:
    st.session_state['input_text'] = ""

def clear_text():
    st.session_state['input_text'] = ""

with st.sidebar:
    st.header("⚙️ Contrôle")
    nom_hippo = st.text_input("Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot", "Plat", "Obstacles"])
    st.divider()
    capital = st.number_input("Capital (€)", value=1000)
    st.button("🧹 Vider les données", on_click=clear_text)
    st.caption("Timeout : 60s | Modèle : 2.5-Flash")

c1, c2 = st.columns([1, 1.3])

with c1:
    txt_in = st.text_area("📋 Partants (Num Nom Fer Musique) :", 
                          value=st.session_state['input_text'], 
                          height=350)
    st.session_state['input_text'] = txt_in
    
    if st.button("🚀 LANCER L'ANALYSE (LIVE)"):
        df = extraire_data_turbo(txt_in)
        if not df.empty:
            with st.spinner(f"📡 Recherche et analyse en cours pour {nom_hippo}..."):
                analyse = analyse_ia_blindee(df, nom_hippo, discipline, capital)
                with c2:
                    st.success("🏁 Analyse Terminée")
                    st.markdown(analyse)
        else:
            st.error("Aucune donnée détectée.")

with c2:
    if not 'analyse' in locals():
        st.info("Cette version dispose d'un délai d'attente étendu pour éviter les erreurs de connexion.")

st.divider()
st.caption("Optimisation Performance 2026 : Connexion Sécurisée.")
