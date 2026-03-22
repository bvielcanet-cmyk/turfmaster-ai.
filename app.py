import streamlit as st
import pandas as pd
import re
import requests
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Force Brute", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente des Secrets.")
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

def expertise_force_v1(df):
    """FORÇAGE DE LA ROUTE V1 (STABLE) VIA HTTP DIRECT"""
    prompt = f"Expert Turf : Analyse ces partants et donne ton top 3 : {df.to_string()}"
    
    # URL FORCÉE EN V1 (On évite le v1beta qui cause ton erreur 404)
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_json = response.json()
        
        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text'], "✅ CONNEXION V1 RÉUSSIE"
        else:
            err_msg = res_json.get('error', {}).get('message', 'Inconnue')
            return None, f"❌ Erreur Serveur {response.status_code}: {err_msg}"
    except Exception as e:
        return None, f"❌ Erreur Réseau : {str(e)}"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Connexion Directe v1")

txt_in = st.text_area("📋 Collez les partants (MAJUSCULES) :", height=150)

if st.button("🚀 FORCER L'ANALYSE"):
    df = extraire_partants(txt_in)
    
    if not df.empty:
        with st.spinner("📦 Tentative de connexion directe (Bypass v1beta)..."):
            expertise, status = expertise_force_v1(df)
            
            if expertise:
                st.success(status)
                st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")
            else:
                st.error(status)
                st.info("💡 Si l'erreur 404 persiste ICI, c'est que votre clé API est rattachée à une région ou un projet restreint.")
    else:
        st.error("Aucun cheval détecté.")
