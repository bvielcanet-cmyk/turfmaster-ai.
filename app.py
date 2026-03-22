import streamlit as st
import pandas as pd
import re
import requests
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Platinum", page_icon="🏇", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Configurez votre nouvelle clé dans les Secrets.")
    st.stop()

# --- 2. FONCTIONS D'ANALYSE ---

def extraire_partants(texte):
    # Capture les noms de chevaux en MAJUSCULES (ex: JIJI DOUZOU)
    noms = re.findall(r'\b[A-Z]{4,}\b', texte)
    return list(dict.fromkeys(noms)) # Supprime les doublons en gardant l'ordre

def expertise_gemini_2_5(noms):
    """APPEL DIRECT AU MODÈLE 2.5 FLASH (NOUVEAUTÉ 2026)"""
    prompt = f"""Expert Turf Platinum : Analyse ces partants et donne ton top 3 favoris. 
    Explique ton choix pour le premier favori.
    Partants : {', '.join(noms)}"""
    
    # On utilise l'ID exact validé par ton scan (Ligne 0)
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        res_json = response.json()
        
        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text'], "🚀 PROPULSÉ PAR GEMINI 2.5 FLASH"
        else:
            return None, f"❌ Erreur {response.status_code} : {res_json.get('error', {}).get('message')}"
    except Exception as e:
        return None, f"❌ Erreur Réseau : {str(e)}"

# --- 3. INTERFACE ---
st.title("🏇 TurfMaster AI : Session Platinum 2.5")
st.success("✅ Connexion établie avec l'infrastructure Google 2026")

txt_in = st.text_area("📋 Collez les partants ici :", height=150, placeholder="VINCENNES - JIJI DOUZOU - FAKIR DU LORAULT")

if st.button("🚀 ANALYSE HAUTE PRÉCISION"):
    noms = extraire_partants(txt_in)
    
    if noms:
        with st.spinner("🧠 Intelligence Artificielle 2.5 en cours d'analyse..."):
            expertise, status = expertise_gemini_2_5(noms)
            
            if expertise:
                st.success(status)
                st.markdown("---")
                st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")
            else:
                st.error(status)
    else:
        st.error("Aucun cheval détecté (noms en MAJUSCULES requis).")

# --- FOOTER ---
st.caption("Moteur : Gemini 2.5 Flash | Compte : Paid Tier France")
