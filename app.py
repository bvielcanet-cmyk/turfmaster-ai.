import streamlit as st
import requests
import re
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Scanner Pro", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente des Secrets.")
    st.stop()

# --- FONCTION DE SCANNER ---
def scanner_modeles_google(noms):
    prompt = f"Expert Turf 2026 : Analyse ces chevaux et donne ton favori : {', '.join(noms)}"
    
    # Liste de tous les IDs de modèles valides en France en 2026
    modeles_a_tester = [
        "gemini-1.5-flash",       # Le plus commun
        "gemini-1.5-pro",         # Le plus puissant (Série 1.5)
        "gemini-2.0-flash-001",   # Série 2.0
        "gemini-pro"              # L'alias universel (Dernier recours)
    ]
    
    for m in modeles_a_tester:
        # On teste la route stable /v1/
        url = f"https://generativelanguage.googleapis.com/v1/models/{m}:generateContent?key={API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                res = response.json()
                text = res['candidates'][0]['content']['parts'][0]['text']
                return text, f"✅ CONNEXION RÉUSSIE VIA : {m.upper()}"
        except:
            continue
            
    return None, "❌ ÉCHEC TOTAL : Aucun modèle (1.5, 2.0, Pro) n'est accessible avec cette clé en France."

# --- INTERFACE ---
st.title("🏇 TurfMaster AI : Scanner de Modèles 2026")
st.info("Statut : Compte Premium (Crédits 254€ Actifs)")

txt_in = st.text_area("📋 Collez les partants (MAJUSCULES) :", "VINCENNES - JIJI DOUZOU - FAKIR DU LORAULT")

if st.button("🚀 LANCER LE SCAN DE CONNEXION"):
    noms = re.findall(r'\b[A-Z]{4,}\b', txt_in)
    if noms:
        with st.spinner("🔄 Scan des serveurs Google en cours..."):
            expertise, status = scanner_modeles_google(noms)
            if expertise:
                st.success(status)
                st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")
            else:
                st.error(status)
                st.warning("""
                ⚠️ **DIAGNOSTIC FINAL :** Si le scan échoue, votre clé API est "orpheline". 
                
                **Solution :** Retournez dans [AI Studio](https://aistudio.google.com/), cliquez sur l'icône **'Engrenage' (Settings)** en bas à gauche, puis **'API Keys'**. Supprimez TOUTES vos clés et créez-en une seule nouvelle dans le projet qui affiche **'Paid Tier'**.
                """)
    else:
        st.error("Aucun nom en MAJUSCULES détecté.")
