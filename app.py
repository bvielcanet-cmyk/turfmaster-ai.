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
        
        # Détecte les noms en MAJUSCULES (Cheval)
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            if current: partants.append(current)
            current = {"num": str(len(partants)+1), "nom": ligne, "cote": 10.0, "musique": "Inconnue"}
        
        # Détecte la COTE (Nombre avec . ou ,)
        elif re.search(r'^\d+[\.,]\d+$', ligne) and current:
            try:
                current["cote"] = float(ligne.replace(',', '.'))
            except ValueError:
                current["cote"] = 10.0 # Valeur par défaut si erreur de conversion
        
        # Détecte la MUSIQUE (Chiffres + lettres comme 1a 2a)
        elif re.search(r'\d+[apmsh]', ligne.lower()) and current:
            current["musique"] = ligne
            
    if current: partants.append(current)
    return pd.DataFrame(partants)

def analyse_directe(df):
    prompt = f"Expert Turf : Analyse ces partants et donne ton top 3 : {df.to_string()}"
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Erreur Google IA : {str(e)}"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Analyseur de Partants")

capital = st.number_input("💰 Votre Capital (€)", value=500)
txt_in = st.text_area("📋 Collez les partants ici (NOMS EN MAJUSCULES) :", height=200, placeholder="JIJI DOUZOU\n26.6\n1a 2a Da")

if st.button("🚀 ANALYSER ET CALCULER LES MISES"):
    if txt_in:
        df = extraire_partants(txt_in)
        
        if not df.empty:
            with st.spinner("🧠 L'IA analyse les données..."):
                expertise = analyse_directe(df)
            
            st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")

            st.write("---")
            st.subheader("📊 Mises Stratégiques (Kelly)")
            
            # Affichage propre
            for i, row in df.iterrows():
                cote = max(row['cote'], 1.01)
                prob = (1 / cote) * 1.15
                kelly = (prob * (cote - 1) - (1 - prob)) / (cote - 1)
                mise = min(max(0, capital * kelly * 0.1), capital * 0.1)

                with st.expander(f"n°{row['num']} - {row['nom']} (Cote: {cote})"):
                    st.write(f"**Mise conseillée :** {round(mise, 2)}€")
                    st.write(f"**Musique :** {row['musique']}")
        else:
            st.error("Aucun cheval détecté. Vérifiez que les NOMS sont en MAJUSCULES.")
    else:
        st.warning("Veuillez coller la liste des partants.")
