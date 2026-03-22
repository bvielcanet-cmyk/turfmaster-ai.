import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Version Blindée", layout="wide")

if "gemini" in st.secrets:
    try:
        # On utilise LangChain pour forcer une connexion propre
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=st.secrets["gemini"]["api_key"],
            temperature=0.3
        )
    except Exception as e:
        st.error(f"Erreur Initialisation : {e}")
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
            partants.append({"num": str(len(partants)+1), "nom": ligne, "cote": 10.0})
    return pd.DataFrame(partants)

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Connexion Forcée (v1 Stable)")

txt_in = st.text_area("📋 Collez les partants (MAJUSCULES) :", height=150)

if st.button("🚀 LANCER L'ANALYSE"):
    if txt_in:
        df = extraire_partants(txt_in)
        
        if not df.empty:
            with st.spinner("🧠 Appel au moteur de secours LangChain..."):
                try:
                    prompt = f"Expert Turf : Analyse ces partants et donne ton top 3 : {df.to_string()}"
                    # Appel via le nouveau moteur
                    response = llm.invoke(prompt)
                    st.success("✅ CONNEXION RÉUSSIE !")
                    st.markdown(f"### 🎯 Verdict de l'IA\n{response.content}")
                except Exception as e:
                    st.error(f"❌ ÉCHEC PERSISTANT : {e}")
                    st.info("💡 Si l'erreur 404 persiste, essayez de changer le nom du modèle dans le code par 'gemini-pro'.")
        else:
            st.error("Aucun cheval détecté.")
