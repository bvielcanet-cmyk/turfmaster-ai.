import streamlit as st
import google.generativeai as genai
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Final Edition", layout="wide")

if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
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
        # Détecte les noms en MAJUSCULES
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            if current: partants.append(current)
            current = {"num": str(len(partants)+1), "nom": ligne, "cote": 10.0, "musique": "Inconnue"}
        elif re.search(r'(\d+[\.,]\d+)', ligne) and current:
            current["cote"] = float(ligne.replace(',', '.'))
        elif re.search(r'\d+[apmsh]', ligne.lower()) and current:
            current["musique"] = ligne
    if current: partants.append(current)
    return pd.DataFrame(partants)

def analyse_directe(df):
    """Analyse sans outils de recherche pour garantir la stabilité"""
    prompt = f"Expert Turf : Analyse ces partants et donne ton top 3 : {df.to_string()}"
    try:
        # Utilisation du modèle le plus universel
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Erreur Google : {str(e)}"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Analyseur de Partants")

capital = st.number_input("💰 Votre Capital (€)", value=500)
txt_in = st.text_area("📋 Collez les partants ici (NOMS EN MAJUSCULES) :", height=200)

if st.button("🚀 ANALYSER ET CALCULER LES MISES"):
    df = extraire_partants(txt_in)
    
    if not df.empty:
        with st.spinner("🧠 L'IA analyse les chances de victoire..."):
            expertise = analyse_directe(df)
        
        st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")

        # --- CALCULS DE MISE (Kelly Criterion) ---
        st.write("---")
        st.subheader("📊 Mises Stratégiques")
        cols = st.columns(min(len(df), 4))
        
        for i, row in df.iterrows():
            if i >= 4: break # On limite l'affichage aux 4 premiers
            
            # Calcul simplifié
            cote = max(row['cote'], 1.01)
            prob_theorique = (1 / cote) * 1.15
            podium_score = min(95, int((prob_theorique ** 0.7) * 200))
            
            # Mise Kelly (10% de fraction pour prudence)
            kelly = (prob_theorique * (cote - 1) - (1 - prob_theorique)) / (cote - 1)
            mise = min(max(0, capital * kelly * 0.1), capital * 0.1)

            with cols[i]:
                st.metric(label=f"n°{row['num']} - {row['nom']}", value=f"{round(mise, 2)}€", delta=f"{podium_score}% Podium")
                st.caption(f"Cote : {cote}")
    else:
        st.error("Aucun cheval détecté. Assurez-vous que les NOMS sont en MAJUSCULES.")
