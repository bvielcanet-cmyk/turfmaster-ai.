import streamlit as st
import google.generativeai as genai
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Nouveau Départ", layout="wide")

if "gemini" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Erreur Config : {e}")
else:
    st.error("❌ Configurez votre NOUVELLE clé API dans les Secrets.")
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

st.title("🏇 TurfMaster AI : Session Réinitialisée")

txt_in = st.text_area("📋 Collez les partants (MAJUSCULES) :", height=150)

if st.button("🚀 LANCER L'ANALYSE"):
    df = extraire_partants(txt_in)
    
    if not df.empty:
        with st.spinner("🧠 Connexion à la nouvelle clé..."):
            try:
                prompt = f"Expert Turf : Analyse ces partants et donne ton top 3 : {df.to_string()}"
                response = model.generate_content(prompt)
                st.success("✅ CONNEXION RÉUSSIE !")
                st.markdown(f"### 🎯 Verdict de l'IA\n{response.text}")
            except Exception as e:
                st.error(f"❌ ÉCHEC avec la nouvelle clé : {e}")
                st.info("Vérifiez que vous avez bien choisi 'New Project' dans AI Studio.")
    else:
        st.error("Aucun cheval détecté.")
