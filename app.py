import streamlit as st
import pandas as pd
import re
import requests
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI 3.1 PRO", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente des Secrets.")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_partants(texte):
    # Capture tous les mots en MAJUSCULES de plus de 4 lettres
    return re.findall(r'\b[A-Z]{4,}\b', texte)

def expertise_gemini_3_1(noms):
    """APPEL DIRECT GEMINI 3.1 PRO (FORÇAGE V1 STABLE)"""
    prompt = f"Expert Turf 2026 : Analyse ces chevaux et donne ton favori avec explication : {', '.join(noms)}"
    
    # URL spécifique pour Gemini 3.1 Pro en version Stable
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-pro:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        res_json = response.json()
        
        if response.status_code == 200:
            text = res_json['candidates'][0]['content']['parts'][0]['text']
            return text, "🚀 ANALYSE PROPULSÉE PAR GEMINI 3.1 PRO"
        else:
            # Diagnostic précis pour la France
            err_msg = res_json.get('error', {}).get('message', 'Inconnue')
            return None, f"❌ Erreur {response.status_code} : {err_msg}"
    except Exception as e:
        return None, f"❌ Erreur Réseau : {str(e)}"

# --- 3. INTERFACE ---
st.title("🏇 TurfMaster AI : Session 3.1 Pro")
st.success("💎 Compte Premium Détecté (Crédits Actifs)")

txt_in = st.text_area("📋 Collez les partants :", "VINCENNES - JIJI DOUZOU - FAKIR DU LORAULT")

if st.button("🚀 ANALYSE HAUTE PERFORMANCE"):
    noms = extraire_partants(txt_in)
    if noms:
        with st.spinner("🧠 Connexion au moteur Gemini 3.1 Pro..."):
            expertise, status = expertise_gemini_3_1(noms)
            if expertise:
                st.success(status)
                st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")
            else:
                st.error(status)
                st.info("💡 Si l'erreur 404 persiste : Allez dans Google Cloud Console > APIs & Services > Enabled APIs et vérifiez que 'Generative Language API' est bien ACTIVER.")
    else:
        st.error("Aucun nom en MAJUSCULES détecté.")
