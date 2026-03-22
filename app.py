import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Ultra-Pro", layout="wide")

# Initialisation du NOUVEAU client (Standard 2026)
if "gemini" in st.secrets:
    try:
        # On force l'utilisation du SDK moderne pour éviter le bug v1beta
        client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
        MODEL_ID = "gemini-2.0-flash" # Le modèle par défaut de ton abonnement Pro
    except Exception as e:
        st.error(f"Erreur Initialisation : {e}")
else:
    st.error("❌ Clé API absente des Secrets.")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_partants(texte):
    partants = []
    lignes = texte.strip().split('\n')
    current = None
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne: continue
        # Détection Nom (MAJUSCULES)
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            if current: partants.append(current)
            current = {"num": str(len(partants)+1), "nom": ligne, "cote": 10.0, "musique": "Inconnu"}
        # Détection Cote
        elif re.match(r'^\d+[\.,]\d+$', ligne) and current:
            try: current["cote"] = float(ligne.replace(',', '.'))
            except: pass
        # Détection Musique
        elif re.search(r'\d+[apmsh]', ligne.lower()) and current:
            current["musique"] = ligne
    if current: partants.append(current)
    return pd.DataFrame(partants)

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Session Pro Débloquée")

capital = st.number_input("💰 Votre Capital (€)", value=500)
txt_in = st.text_area("📋 Collez les partants ici :", height=150)

if st.button("🚀 ANALYSER LA COURSE"):
    if txt_in:
        df = extraire_partants(txt_in)
        
        if not df.empty:
            # APPEL IA AVEC LE NOUVEAU SDK (SANS v1beta)
            with st.spinner("🧠 Analyse Pro en cours..."):
                try:
                    prompt = f"Expert Turf : Analyse ces partants et donne ton top 3 : {df.to_string()}"
                    # Syntaxe 2026 pure
                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=prompt
                    )
                    st.success("✅ Connexion Pro Réussie")
                    st.markdown(f"### 🎯 Verdict de l'IA\n{response.text}")
                except Exception as e:
                    st.warning(f"⚠️ Mode Statistique Uniquement (IA : {e})")

            # --- CALCULS ---
            st.write("---")
            cols = st.columns(min(len(df), 4))
            for i, row in df.iterrows():
                if i >= 4: break
                cote = max(row['cote'], 1.01)
                prob = (1 / cote) * 1.15
                kelly = (prob * (cote - 1) - (1 - prob)) / (cote - 1)
                mise = min(max(0, capital * kelly * 0.1), capital * 0.1)
                with cols[i]:
                    st.metric(label=f"n°{row['num']} - {row['nom']}", value=f"{round(mise, 2)}€")
                    st.caption(f"Cote: {cote} | Musique: {row['musique']}")
        else:
            st.error("Aucun cheval détecté.")
