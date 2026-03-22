import streamlit as st
import pandas as pd
import re
import requests
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Final Fix", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente des Secrets.")
    st.stop()

# --- 2. FONCTION DE CONNEXION ---
def expertise_alias_universel(df):
    """Utilise l'alias 'gemini-pro' qui est le plus robuste au 404"""
    prompt = f"Expert Turf : Analyse ces chevaux et donne ton top 3 : {df['nom'].tolist()}"
    
    # URL utilisant l'alias universel sur la route v1beta (plus permissive)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        res_json = response.json()
        
        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text'], "✅ SUCCÈS (MODE PRO)"
        else:
            err_msg = res_json.get('error', {}).get('message', 'Inconnue')
            return None, f"❌ Erreur {response.status_code}: {err_msg}"
    except Exception as e:
        return None, f"❌ Erreur Réseau : {str(e)}"

# --- 3. INTERFACE ---
st.title("🏇 TurfMaster AI : Connexion Forcée")

txt_in = st.text_area("📋 Collez les partants (MAJUSCULES) :", height=150)

if st.button("🚀 LANCER L'ANALYSE FINALE"):
    noms = re.findall(r'\b[A-Z]{4,}\b', txt_in)
    if noms:
        df = pd.DataFrame({"nom": noms})
        with st.spinner("🧠 Tentative de connexion via l'alias universel..."):
            expertise, status = expertise_alias_universel(df)
            
            if expertise:
                st.success(status)
                st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")
            else:
                st.error(status)
                st.info("💡 Si l'erreur 404 persiste, allez sur Google AI Studio et cliquez sur 'Create API key in NEW project'.")
    else:
        st.error("Aucun nom en MAJUSCULES détecté.")
