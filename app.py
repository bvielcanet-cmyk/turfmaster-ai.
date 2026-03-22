import streamlit as st
import pandas as pd
import re
import requests

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Final Edition", layout="wide")

# On récupère la NOUVELLE clé
if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Mettez la nouvelle clé API dans les Secrets Streamlit.")
    st.stop()

# --- 2. FONCTIONS ---

def expertise_pro_france(noms):
    prompt = f"Expert Turf France : Analyse ces chevaux et donne ton favori avec une explication courte : {', '.join(noms)}"
    
    # URL Stable v1 (Fonctionne uniquement si le Billing est activé)
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        res_json = response.json()
        
        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"❌ Erreur {response.status_code} : {res_json.get('error', {}).get('message')}"
    except Exception as e:
        return f"❌ Erreur de connexion : {e}"

# --- 3. INTERFACE ---
st.title("🏇 TurfMaster AI : Analyseur Débridé")

txt_in = st.text_area("📋 Collez les partants (NOMS EN MAJUSCULES) :", height=150)

if st.button("🚀 ANALYSER LA COURSE"):
    # Extraction propre des noms
    noms_trouves = re.findall(r'\b[A-Z]{4,}\b', txt_in)
    
    if noms_trouves:
        st.info(f"🔎 {len(noms_trouves)} chevaux détectés. Envoi à l'IA...")
        with st.spinner("🧠 Analyse en cours..."):
            resultat = expertise_pro_france(noms_trouves)
            st.markdown("### 🎯 Verdict de l'IA")
            st.write(resultat)
    else:
        st.error("Aucun nom en MAJUSCULES détecté (ex: JIJI DOUZOU).")
