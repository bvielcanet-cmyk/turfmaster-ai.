import streamlit as st
import pandas as pd
import re
import requests
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Final Edition", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Configurez votre clé API dans les Secrets.")
    st.stop()

# --- LOGIQUE ---
def expertise_directe(df):
    prompt = f"Expert Turf : Analyse ces partants et donne ton top 3 : {df.to_string()}"
    # Utilisation de la route v1 (stable) avec le modèle Flash
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload, timeout=20)
        res_json = response.json()
        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text'], "✅ SUCCÈS"
        else:
            return None, f"Erreur {response.status_code}: {res_json.get('error', {}).get('message')}"
    except Exception as e:
        return None, f"Erreur Réseau : {e}"

# --- INTERFACE ---
st.title("🏇 TurfMaster AI : Analyseur Pro")

txt_in = st.text_area("📋 Collez les partants (NOMS EN MAJUSCULES) :")

if st.button("🚀 ANALYSER LA COURSE"):
    # Extraction simple des noms en MAJUSCULES
    noms = re.findall(r'\b[A-Z]{4,}\b', txt_in)
    if noms:
        df = pd.DataFrame({"nom": noms})
        with st.spinner("🧠 Analyse IA en cours..."):
            expertise, status = expertise_directe(df)
            
            if expertise:
                st.success(status)
                st.markdown(expertise)
            else:
                st.error(status)
                st.info("⚠️ Si l'erreur 404 persiste : Activez le 'Billing' dans la console Google Cloud.")
    else:
        st.error("Aucun nom en MAJUSCULES détecté.")
