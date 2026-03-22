import streamlit as st
import pandas as pd
import re
import requests
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Final Edition", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Configurez votre clé API dans les Secrets Streamlit.")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_partants(texte):
    noms = re.findall(r'\b[A-Z]{4,}\b', texte)
    return pd.DataFrame({"nom": noms})

def expertise_force_v1(df):
    """FORÇAGE DE LA ROUTE V1 (STABLE) VIA HTTP DIRECT"""
    prompt = f"Expert Turf : Analyse ces chevaux et donne ton top 3 : {df['nom'].tolist()}"
    
    # URL FORCÉE EN V1 (On évite le v1beta qui cause ton erreur 404)
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        res_json = response.json()
        
        if response.status_code == 200:
            # Succès ! On extrait le texte
            return res_json['candidates'][0]['content']['parts'][0]['text'], "✅ CONNEXION RÉUSSIE (V1)"
        else:
            # Erreur détaillée du serveur
            err_msg = res_json.get('error', {}).get('message', 'Inconnue')
            return None, f"❌ Erreur Serveur {response.status_code}: {err_msg}"
    except Exception as e:
        return None, f"❌ Erreur Réseau : {str(e)}"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Mode Direct v1")
st.caption("Statut : Compte Débridé (Paid Tier)")

txt_in = st.text_area("📋 Collez les partants (NOMS EN MAJUSCULES) :", height=150)

if st.button("🚀 LANCER L'ANALYSE PRO"):
    df = extraire_partants(txt_in)
    
    if not df.empty:
        with st.spinner("📦 Communication directe avec les serveurs de production..."):
            expertise, status = expertise_force_v1(df)
            
            if expertise:
                st.success(status)
                st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")
            else:
                st.error(status)
    else:
        st.error("Aucun nom en MAJUSCULES détecté.")
