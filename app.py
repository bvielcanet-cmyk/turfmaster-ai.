import streamlit as st
import google.generativeai as genai
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI GOLD", page_icon="🏇", layout="wide")

# Connexion avec ta clé API (Compte Paid Tier / France)
if "gemini" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        # On utilise le modèle 1.5 Flash (le plus stable et rapide en France)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Erreur de configuration API : {e}")
else:
    st.error("❌ Clé API absente des Secrets Streamlit.")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_partants(texte):
    partants = []
    lignes = texte.strip().split('\n')
    for ligne in lignes:
        ligne = ligne.strip()
        # Détection simple des noms en MAJUSCULES
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            partants.append({"num": str(len(partants)+1), "nom": ligne})
    return pd.DataFrame(partants)

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Session Gold Débridée")
st.caption("Statut : Compte avec Facturation Active (France)")

txt_in = st.text_area("📋 Collez les partants (NOMS EN MAJUSCULES) :", height=150)

if st.button("🚀 LANCER L'ANALYSE"):
    df = extraire_partants(txt_in)
    
    if not df.empty:
        with st.spinner("🧠 L'IA analyse les partants via votre accès Pro..."):
            try:
                prompt = f"Expert Turf : Analyse ces chevaux et donne ton favori avec une explication courte : {df['nom'].tolist()}"
                response = model.generate_content(prompt)
                
                st.success("✅ Connexion Réussie !")
                st.markdown("### 🎯 Verdict de l'IA")
                st.write(response.text)
            except Exception as e:
                st.error(f"Erreur lors de l'appel IA : {e}")
    else:
        st.error("Aucun nom en MAJUSCULES détecté (ex: JIJI DOUZOU).")
