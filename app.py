import streamlit as st
import requests

st.title("🏇 TurfMaster AI : Debug Final")

# Remplace ici avec la toute nouvelle clé créée dans Google Cloud (pas AI Studio)
API_KEY = st.secrets["gemini"]["api_key"]

if st.button("🔍 SCANNER MON COMPTE GOOGLE"):
    # On demande à Google : "Quels modèles m'autorises-tu à utiliser en France ?"
    url = f"https://generativelanguage.googleapis.com/v1/models?key={API_KEY}"
    
    try:
        response = requests.get(url)
        res = response.json()
        
        if response.status_code == 200:
            st.success("✅ CONNEXION RÉUSSIE !")
            st.write("Voici les modèles que votre compte autorise :")
            # On liste les modèles disponibles pour ta clé
            modeles = [m['name'] for m in res.get('models', [])]
            st.json(modeles)
            
            if "models/gemini-1.5-flash" in modeles or "models/gemini-pro" in modeles:
                st.info("💡 Votre clé est maintenant prête. On peut relancer l'analyse !")
        else:
            st.error(f"❌ Erreur {response.status_code} : {res.get('error', {}).get('message')}")
            st.write("Diagnostic : Votre clé est active mais le service 'Generative Language' n'est pas activé sur ce projet.")
    except Exception as e:
        st.error(f"Erreur réseau : {e}")
