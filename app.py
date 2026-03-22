import streamlit as st
import pandas as pd
import re
import requests
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Force Alpha", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente des Secrets.")
    st.stop()

# --- FONCTION DE CONNEXION ---
def expertise_ultime_france(noms):
    prompt = f"Expert Turf : Analyse ces chevaux et donne ton favori : {', '.join(noms)}"
    
    # On teste l'URL la plus simple possible (v1beta / gemini-pro)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        res_json = response.json()
        
        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text'], "✅ CONNEXION RÉUSSIE"
        else:
            # Si 404, on affiche un message d'aide spécifique à la France
            err = res_json.get('error', {}).get('message', 'Inconnue')
            return None, f"❌ Erreur {response.status_code} : {err}"
    except Exception as e:
        return None, f"❌ Erreur Réseau : {str(e)}"

# --- INTERFACE ---
st.title("🏇 TurfMaster AI : Session France Pro")

txt_in = st.text_area("📋 Collez les partants (MAJUSCULES) :", "VINCENNES - JIJI DOUZOU - FAKIR DU LORAULT")

if st.button("🚀 TESTER LA CONNEXION"):
    noms = re.findall(r'\b[A-Z]{4,}\b', txt_in)
    if noms:
        with st.spinner("🧠 Tentative de connexion finale..."):
            expertise, status = expertise_ultime_france(noms)
            if expertise:
                st.success(status)
                st.write(expertise)
            else:
                st.error(status)
                st.warning("⚠️ ACTION REQUISE : Allez dans la Console Google Cloud, désactivez puis réactivez 'Generative Language API'.")
    else:
        st.error("Aucun nom en MAJUSCULES détecté.")
