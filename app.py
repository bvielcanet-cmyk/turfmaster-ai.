import streamlit as st
import pandas as pd
import re
import requests
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Force Alpha", layout="wide")

# Récupération de la clé API
if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente des Secrets.")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_partants(texte):
    # On cherche les noms de chevaux (MAJUSCULES de plus de 4 lettres)
    noms = re.findall(r'\b[A-Z]{4,}\b', texte)
    return list(set(noms)) # On évite les doublons

def expertise_ultime(noms):
    """Tentative sur l'ID de production exact pour la France"""
    prompt = f"Expert Turf : Analyse ces chevaux et donne ton favori : {', '.join(noms)}"
    
    # On utilise l'ID de version fixe (-001) qui est obligatoire sur certains comptes payants
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-001:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        res_json = response.json()
        
        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text'], "✅ SUCCÈS (PROD-001)"
        else:
            # Si échec, on tente le modèle Pro version fixe
            url_pro = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro-001:generateContent?key={API_KEY}"
            resp_pro = requests.post(url_pro, json=payload, timeout=15)
            if resp_pro.status_code == 200:
                return resp_pro.json()['candidates'][0]['content']['parts'][0]['text'], "✅ SUCCÈS (PRO-001)"
            
            err = res_json.get('error', {}).get('message', 'Inconnue')
            return None, f"❌ Erreur {response.status_code} : {err}"
    except Exception as e:
        return None, f"❌ Erreur Réseau : {str(e)}"

# --- 3. INTERFACE ---
st.title("🏇 TurfMaster AI : Connexion Haute Fidélité")

txt_in = st.text_area("📋 Collez les partants (EX: JIJI DOUZOU) :", height=150)

if st.button("🚀 ANALYSER LA COURSE"):
    noms = extraire_partants(txt_in)
    if noms:
        with st.spinner("🧠 Appel aux serveurs de production Google..."):
            expertise, status = expertise_ultime(noms)
            if expertise:
                st.success(status)
                st.write(expertise)
            else:
                st.error(status)
                st.markdown("### 📢 SOLUTION FINALE SI ÇA ÉCHOUE :")
                st.write("""
                En France, si le 404 persiste avec '0 crédits utilisés sur 254 €', c'est que votre clé est sur un **'Projet par défaut'**. 
                
                **Action :** Allez sur [Google AI Studio](https://aistudio.google.com/), cliquez sur **'Create API Key'** et vérifiez bien que vous sélectionnez le projet nommé **'Generative Language Client'** (celui créé par Google pour votre abonnement à 20€).
                """)
    else:
        st.error("Aucun nom en MAJUSCULES détecté.")
