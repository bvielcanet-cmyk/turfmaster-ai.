import streamlit as st
import requests
import re
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Global Force", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente.")
    st.stop()

# --- FONCTION DE CONNEXION ---
def expertise_global_france(noms):
    prompt = f"Expert Turf 2026 : Analyse ces chevaux et donne ton favori : {', '.join(noms)}"
    
    # En 2026, l'endpoint global est parfois le seul qui accepte les comptes payants en France
    # On teste le modèle 'gemini-1.5-flash-8b' qui est le plus 'léger' et passe partout
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-8b:generateContent?key={API_KEY}"
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        res_json = response.json()
        
        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text'], "✅ CONNEXION RÉUSSIE (GLOBAL FLASH)"
        else:
            # Si échec, on tente le modèle 'gemini-1.5-pro' avec une URL différente
            url_pro = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={API_KEY}"
            resp_pro = requests.post(url_pro, headers=headers, json=payload, timeout=15)
            if resp_pro.status_code == 200:
                return resp_pro.json()['candidates'][0]['content']['parts'][0]['text'], "✅ CONNEXION RÉUSSIE (PRO)"
            
            return None, f"❌ Erreur {response.status_code} : {res_json.get('error', {}).get('message')}"
    except Exception as e:
        return None, f"❌ Erreur Réseau : {str(e)}"

# --- INTERFACE ---
st.title("🏇 TurfMaster AI : Session France (Global)")
st.info("Statut : Compte avec 254€ de crédits - Scan Global")

txt_in = st.text_area("📋 Collez les partants (MAJUSCULES) :", "VINCENNES - JIJI DOUZOU")

if st.button("🚀 LANCER LA CONNEXION GLOBALE"):
    noms = re.findall(r'\b[A-Z]{4,}\b', txt_in)
    if noms:
        with st.spinner("🧠 Tentative de percée via l'endpoint global..."):
            expertise, status = expertise_global_france(noms)
            if expertise:
                st.success(status)
                st.write(expertise)
            else:
                st.error(status)
                st.warning("""
                ⚠️ **DERNIÈRE ÉTAPE POSSIBLE :** Votre clé est active mais le modèle est bloqué. 
                1. Allez dans [AI Studio](https://aistudio.google.com/).
                2. Cliquez sur 'Create API key in NEW project'. 
                3. **Important :** Choisissez un nom de projet totalement différent (ex: 'TurfApp2026').
                """)
    else:
        st.error("Aucun nom en MAJUSCULES détecté.")
