import streamlit as st
import google.generativeai as genai
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Final Fix", layout="wide")

# Utilisation de la configuration la plus stable possible
if "gemini" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        # On définit le modèle sur 'gemini-pro', c'est le plus compatible
        model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        st.error(f"Erreur de configuration : {e}")
else:
    st.error("❌ Configurez votre clé API dans les Secrets Streamlit.")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_partants(texte):
    partants = []
    lignes = texte.strip().split('\n')
    current = None
    
    for i, ligne in enumerate(lignes):
        ligne = ligne.strip()
        if not ligne: continue
        
        # Détection Nom (MAJUSCULES)
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            if current: partants.append(current)
            current = {"num": str(len(partants)+1), "nom": ligne, "cote": 10.0, "musique": "Inconnue"}
        
        # Détection Cote (Nombre seul sur la ligne)
        elif re.match(r'^\d+[\.,]\d+$', ligne) and current:
            try:
                current["cote"] = float(ligne.replace(',', '.'))
            except:
                pass
        
        # Détection Musique
        elif re.search(r'\d+[apmsh]', ligne.lower()) and current:
            current["musique"] = ligne
            
    if current: partants.append(current)
    return pd.DataFrame(partants)

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Analyseur de Partants")

capital = st.number_input("💰 Votre Capital (€)", value=500)
txt_in = st.text_area("📋 Collez les partants ici (NOMS EN MAJUSCULES) :", height=200)

if st.button("🚀 LANCER L'ANALYSE"):
    if txt_in:
        df = extraire_partants(txt_in)
        
        if not df.empty:
            with st.spinner("🧠 L'IA analyse les données..."):
                try:
                    # Appel ultra-simplifié sans paramètres complexes
                    prompt = f"Expert Turf : Analyse ces partants et donne ton top 3 : {df.to_string()}"
                    response = model.generate_content(prompt)
                    expertise = response.text
                    st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")
                except Exception as e:
                    st.error(f"⚠️ Note : L'IA est indisponible ({e}). Voici l'analyse statistique :")

            # --- CALCULS STATISTIQUES (Fonctionnent toujours) ---
            st.write("---")
            st.subheader("📊 Mises Stratégiques (Kelly)")
            
            cols = st.columns(min(len(df), 4))
            for i, row in df.iterrows():
                if i >= 4: break # Max 4 colonnes
                
                cote = max(row['cote'], 1.01)
                prob = (1 / cote) * 1.15
                kelly = (prob * (cote - 1) - (1 - prob)) / (cote - 1)
                mise = min(max(0, capital * kelly * 0.1), capital * 0.1)

                with cols[i]:
                    st.metric(label=f"n°{row['num']} - {row['nom']}", value=f"{round(mise, 2)}€", delta=f"Cote: {cote}")
                    st.caption(f"Musique: {row['musique']}")
        else:
            st.error("Aucun cheval détecté (Noms en MAJUSCULES requis).")
    else:
        st.warning("Veuillez coller la liste des partants.")
