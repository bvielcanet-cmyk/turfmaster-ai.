import streamlit as st
import pandas as pd
import re
import requests
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : France Pro", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente des Secrets Streamlit.")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_partants(texte):
    partants = []
    lignes = texte.strip().split('\n')
    for ligne in lignes:
        ligne = ligne.strip()
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            partants.append({"num": str(len(partants)+1), "nom": ligne})
    return pd.DataFrame(partants)

def expertise_france_pro(df):
    """Configuration spécifique pour contourner le 404 en France/Europe"""
    prompt = f"Expert Turf France : Analyse ces partants et donne ton top 3 : {df.to_string()}"
    
    # En France, gemini-1.5-pro est souvent mieux supporté sur l'API v1beta
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.5,
            "topP": 0.8,
            "topK": 40
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        res_json = response.json()
        
        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text'], "✅ CONNEXION FRANCE RÉUSSIE"
        else:
            # Si le 1.5-pro échoue, on tente l'alias universel 'gemini-pro'
            url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"
            resp_fb = requests.post(url_fallback, headers=headers, json=payload, timeout=20)
            if resp_fb.status_code == 200:
                return resp_fb.json()['candidates'][0]['content']['parts'][0]['text'], "✅ CONNEXION FRANCE RÉUSSIE (MODE COMPATIBILITÉ)"
            
            err_msg = res_json.get('error', {}).get('message', 'Erreur inconnue')
            return None, f"❌ Erreur {response.status_code} (France) : {err_msg}"
    except Exception as e:
        return None, f"❌ Erreur Réseau : {str(e)}"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Expertise Pro (France)")

txt_in = st.text_area("📋 Collez les partants (NOMS EN MAJUSCULES) :", height=150)

if st.button("🚀 LANCER L'ANALYSE PRO"):
    df = extraire_partants(txt_in)
    
    if not df.empty:
        with st.spinner("🧠 Analyse sécurisée via les serveurs européens..."):
            expertise, status = expertise_france_pro(df)
            
            if expertise:
                st.success(status)
                st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")
            else:
                st.error(status)
                st.info("💡 CONSEIL FINAL : En France, Google exige souvent que le compte soit 'Payant' (Pay-as-you-go) pour activer l'API, même avec l'abonnement Pro à 20€.")
    else:
        st.error("Aucun cheval détecté.")
