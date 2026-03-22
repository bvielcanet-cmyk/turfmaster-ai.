import streamlit as st
from google import genai
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Debug", layout="wide")

if "gemini" in st.secrets:
    client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("❌ Clé API absente des Secrets Streamlit.")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_partants(texte):
    partants = []
    lignes = texte.strip().split('\n')
    for i, ligne in enumerate(lignes):
        ligne = ligne.strip()
        if ligne.isupper() and len(ligne) > 3:
            partants.append({"num": str(len(partants)+1), "nom": ligne, "cote": 10.0})
    return pd.DataFrame(partants)

def expertise_diagnostic(df):
    """Test de connexion ultra-simplifié"""
    prompt = f"Analyse ces chevaux de course et donne un favori : {df['nom'].tolist()}"
    
    # LISTE DES MODÈLES À TESTER (DU PLUS RÉCENT AU PLUS STABLE)
    modeles = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    derniere_erreur = ""
    
    for m in modeles:
        try:
            # ON TESTE SANS RECHERCHE WEB POUR ISOLER LE PROBLÈME
            response = client.models.generate_content(model=m, contents=prompt)
            return response.text, f"✅ FONCTIONNE AVEC {m}"
        except Exception as e:
            derniere_erreur = str(e)
            continue # On tente le modèle suivant
            
    return None, f"❌ ERREUR GOOGLE : {derniere_erreur}"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Diagnostic Force")

txt_in = st.text_area("📋 Collez vos partants (MAJUSCULES) :")

if st.button("🚀 TESTER LA CONNEXION MAINTENANT"):
    df = extraire_partants(txt_in)
    
    if not df.empty:
        with st.spinner("Appel à Google IA en cours..."):
            expertise, status = expertise_diagnostic(df)
        
        # AFFICHAGE DU RÉSULTAT
        st.subheader("Résultat du Diagnostic :")
        st.code(status) # Affiche l'erreur brute pour qu'on puisse la lire
        
        if expertise:
            st.success("L'IA a répondu !")
            st.write(expertise)
    else:
        st.error("Aucun nom en MAJUSCULES détecté.")
