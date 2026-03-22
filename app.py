import streamlit as st
import google.generativeai as palai # On change de moteur pour plus de stabilité
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Final Fix", layout="wide")

# Initialisation avec l'ancienne syntaxe (plus robuste aux erreurs 404)
if "gemini" in st.secrets:
    palai.configure(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("❌ Clé API absente des Secrets.")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_partants(texte):
    partants = []
    lignes = texte.strip().split('\n')
    for ligne in lignes:
        ligne = ligne.strip()
        if ligne.isupper() and len(ligne) > 3:
            partants.append({"num": str(len(partants)+1), "nom": ligne, "cote": 10.0})
    return pd.DataFrame(partants)

def expertise_ultime(df):
    """Test de connexion avec la syntaxe la plus stable possible"""
    prompt = f"En tant qu'expert turf, analyse ces chevaux et donne un favori : {df['nom'].tolist()}"
    
    # On teste les noms de modèles standards
    for m_name in ['gemini-1.5-flash', 'gemini-pro', 'gemini-1.5-pro']:
        try:
            model = palai.GenerativeModel(m_name)
            # On retire la recherche web pour l'instant pour garantir la connexion
            response = model.generate_content(prompt)
            return response.text, f"✅ CONNECTÉ VIA {m_name.upper()}"
        except Exception as e:
            continue
            
    return None, "❌ ÉCHEC CRITIQUE : Google ne reconnaît aucun modèle avec cette clé."

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Connexion Forcée")

txt_in = st.text_area("📋 Collez vos partants (MAJUSCULES) :", height=150)

if st.button("🚀 FORCER L'ANALYSE"):
    df = extraire_partants(txt_in)
    
    if not df.empty:
        with st.spinner("📦 Tentative de connexion aux serveurs Google..."):
            expertise, status = expertise_ultime(df)
        
        # AFFICHAGE DU STATUT
        if "✅" in status:
            st.success(status)
            st.markdown(f"""<div style="background-color:#f0f7ff; padding:20px; border-radius:10px; border-left:5px solid #007bff; color:#0d47a1;">
                {expertise}</div>""", unsafe_allow_html=True)
            
            # --- CALCULS DE BASE ---
            st.write("---")
            st.subheader("📊 Mises suggérées (Calculateur Interne)")
            cols = st.columns(len(df[:4])) # On affiche les 4 premiers
            for i, row in df[:4].iterrows():
                with cols[i]:
                    st.metric(label=row['nom'], value=f"n°{row['num']}", delta="Prêt")
        else:
            st.error(status)
            st.info("💡 CONSEIL : Si l'erreur persiste, créez une nouvelle clé API sur Google AI Studio en choisissant un projet 'Pay-as-you-go'.")
    else:
        st.error("Aucun nom en MAJUSCULES détecté.")
