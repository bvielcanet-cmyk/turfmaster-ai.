import streamlit as st
from google import genai
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Ultra-Performance", layout="wide")

# Initialisation du client moderne 2026
if "gemini" in st.secrets:
    try:
        client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
    except Exception as e:
        st.error(f"Erreur Initialisation Client : {e}")
else:
    st.error("❌ Clé API absente des Secrets Streamlit.")
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
            current = {"num": str(len(partants)+1), "nom": ligne, "cote": 10.0, "musique": "Inconnue"}
        # Détection Cote
        elif re.match(r'^\d+[\.,]\d+$', ligne) and current:
            try: current["cote"] = float(ligne.replace(',', '.'))
            except: pass
        # Détection Musique
        elif re.search(r'\d+[apmsh]', ligne.lower()) and current:
            current["musique"] = ligne
    if current: partants.append(current)
    return pd.DataFrame(partants)

def expertise_multi_modeles(df):
    """Teste les modèles de pointe incluant Gemini 3.1"""
    prompt = f"Expert Turf Haute Performance : Analyse ces partants et donne ton top 3 : {df.to_string()}"
    
    # Liste des IDs incluant la version 3.1 et les versions stables
    modeles_prioritaires = [
        "gemini-3.1-flash",       # La nouvelle version demandée
        "gemini-3.1-pro",         # Version Pro 3.1
        "gemini-2.0-flash-001",    # Production 2.0
        "gemini-1.5-flash-latest"  # Stable 1.5
    ]
    
    derniere_erreur = ""
    for model_id in modeles_prioritaires:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            return response.text, f"🚀 ANALYSE PROPULSÉE PAR {model_id.upper()}"
        except Exception as e:
            derniere_erreur = str(e)
            # On continue de chercher si le modèle n'est pas trouvé (404) ou pas supporté
            if "404" in derniere_erreur or "not found" in derniere_erreur.lower():
                continue 
            return None, f"❌ Erreur API : {derniere_erreur}"
            
    return None, f"❌ Aucun modèle (3.1/2.0/1.5) n'a répondu. Erreur : {derniere_erreur}"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Session Haute Fidélité")

capital = st.number_input("💰 Votre Capital (€)", value=500)
txt_in = st.text_area("📋 Collez les partants ici (NOMS EN MAJUSCULES) :", height=150)

if st.button("🔍 ANALYSER LA COURSE"):
    if txt_in:
        df = extraire_partants(txt_in)
        
        if not df.empty:
            with st.spinner("📦 Connexion aux serveurs Gemini 3.1..."):
                expertise, status = expertise_multi_modeles(df)
            
            if expertise:
                st.success(status)
                st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")
            else:
                st.error(status)
                st.warning("Mode Statistique activé.")

            # --- CALCULS DE MISE ---
            st.write("---")
            st.subheader("📊 Mises suggérées (Algorithme Kelly)")
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
    else:
        st.warning("Veuillez coller la liste des partants.")
