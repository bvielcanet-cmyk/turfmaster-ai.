import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Debug", layout="wide")

# TEST DE PRÉSENCE DE LA CLÉ
if "gemini" in st.secrets:
    try:
        api_key = st.secrets["gemini"]["api_key"]
        client = genai.Client(api_key=api_key)
        st.sidebar.success("✅ Clé API détectée dans les secrets")
    except Exception as e:
        st.sidebar.error(f"❌ Erreur configuration clé : {e}")
else:
    st.sidebar.error("❌ AUCUNE CLÉ DANS STREAMLIT SECRETS")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_partants(texte):
    partants = []
    lignes = texte.strip().split('\n')
    current = None
    for i, ligne in enumerate(lignes):
        ligne = ligne.strip()
        if not ligne: continue
        if ligne.isupper() and len(ligne) > 3:
            if current: partants.append(current)
            current = {"num": "1", "nom": ligne, "cote": 10.0, "musique": "Inconnue"}
        elif re.search(r'(\d+[\.,]\d+)', ligne):
            if current: current["cote"] = float(ligne.replace(',', '.'))
    if current: partants.append(current)
    return pd.DataFrame(partants)

def analyse_ia_directe(prompt_text):
    """Tentative d'appel simple sans outils complexes pour tester la connexion"""
    try:
        # TEST 1 : APPEL SIMPLE (Sans recherche web pour isoler le problème)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt_text
        )
        return response.text, "🔹 MODE SIMPLE (IA OK)"
    except Exception as e:
        return None, f"❌ ÉCHEC TOTAL API : {str(e)}"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Test de Connexion")

txt_in = st.text_area("📋 Collez vos partants ici (NOMS EN MAJUSCULES) :")

if st.button("🚀 LANCER L'ANALYSE DE TEST"):
    df = extraire_partants(txt_in)
    
    if not df.empty:
        st.info(f"📊 {len(df)} chevaux détectés. Tentative de connexion à Google IA...")
        
        # APPEL À L'IA
        expertise, status = analyse_ia_directe(f"Analyse ces chevaux : {df['nom'].tolist()}")
        
        # AFFICHAGE DU RÉSULTAT DE L'APPEL
        if expertise:
            st.markdown(f"""
            <div style="background-color: #d4edda; color: #155724; padding: 15px; border-radius: 10px; border: 2px solid #c3e6cb;">
                <h3>{status}</h3>
                <p>{expertise}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Calculs de base pour vérifier que le reste du code suit
            st.success("✅ Le moteur de calcul est prêt à prendre le relais.")
        else:
            st.markdown(f"""
            <div style="background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 10px; border: 2px solid #f5c6cb;">
                <h3>{status}</h3>
                <p>L'IA n'a pas répondu. Vérifiez si votre clé API est 'Active' dans Google AI Studio.</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("❌ Aucun cheval détecté. Vérifiez que les noms sont en MAJUSCULES.")
