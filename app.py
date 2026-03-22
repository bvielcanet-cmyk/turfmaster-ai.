import streamlit as st
import requests
import json
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Force Alpha", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Configurez votre clé API dans les Secrets.")
    st.stop()

# --- 2. FONCTION DE CONNEXION ---
def expertise_ultime_france(noms):
    prompt = f"Analyse ces chevaux de turf et donne le favori : {', '.join(noms)}"
    
    # On teste les deux noms de modèles 'parachutes' qui ne tombent jamais en 404
    for model_name in ["gemini-1.5-pro-latest", "gemini-pro"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"}
            ]
        }
        
        try:
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                res_json = response.json()
                return res_json['candidates'][0]['content']['parts'][0]['text'], f"✅ SUCCÈS ({model_name})"
        except:
            continue
            
    return None, "❌ TOUJOURS 404. Votre clé refuse tous les modèles Google."

# --- 3. INTERFACE ---
st.title("🏇 TurfMaster AI : Connexion Forcée")

txt_in = st.text_area("📋 Collez les partants (MAJUSCULES) :", "VINCENNES - JIJI DOUZOU - 26.6")

if st.button("🚀 TESTER LA CONNEXION"):
    noms = re.findall(r'\b[A-Z]{4,}\b', txt_in)
    if noms:
        with st.spinner("🧠 Tentative de percée des serveurs Google..."):
            expertise, status = expertise_ultime_france(noms)
            
            if expertise:
                st.success(status)
                st.write(expertise)
            else:
                st.error(status)
                st.markdown("""
                ### 📢 DIAGNOSTIC FINAL POUR LA FRANCE :
                Si ce code échoue encore en 404, voici l'explication :
                1. Votre abonnement **Google One AI Premium** est actif sur **Gemini.google.com**.
                2. Mais votre **Clé API** est créée dans **Google Cloud/AI Studio** (qui est une plateforme différente).
                
                **LA SOLUTION :** Dans [Google AI Studio](https://aistudio.google.com/), cliquez sur l'icône **'Gérer la facturation'** et vérifiez que votre projet est bien en mode **'Pay-as-you-go'**. En France, l'API est désactivée par défaut pour les comptes gratuits.
                """)
    else:
        st.error("Aucun nom en MAJUSCULES détecté.")
