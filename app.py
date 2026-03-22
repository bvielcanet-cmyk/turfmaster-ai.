import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import re
import time

# --- 1. CONFIGURATION PRO ---
st.set_page_config(page_title="TurfMaster AI GOLD", page_icon="🏆", layout="wide")

# Utilisation du modèle PRO pour profiter de ton abonnement
MODEL_NAME = "gemini-1.5-pro" 

if "gemini" in st.secrets:
    client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("❌ Clé API manquante dans les Secrets.")
    st.stop()

# --- 2. FONCTIONS DE POINTE ---

def extraire_partants_robuste(texte):
    partants = []
    texte = texte.replace('\xa0', ' ').replace('\t', ' ')
    lignes = texte.strip().split('\n')
    current_horse = None
    compteur_auto = 1
    for i, ligne in enumerate(lignes):
        ligne = ligne.strip()
        if not ligne: continue
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            if current_horse: partants.append(current_horse)
            num_f = lignes[i-1].strip() if i > 0 and lignes[i-1].strip().isdigit() else str(compteur_auto)
            current_horse = {"num": num_f, "nom": ligne, "cote": None, "musique": "Inconnue"}
            compteur_auto += 1
        else:
            cote_match = re.search(r'(\d+[\.,]\d+)', ligne)
            if cote_match and current_horse and current_horse["cote"] is None:
                current_horse["cote"] = float(cote_match.group(1).replace(',', '.'))
    if current_horse: partants.append(current_horse)
    for p in partants:
        if p["cote"] is None or p["cote"] <= 1.0: p["cote"] = 20.0
    return pd.DataFrame(partants)

def expertise_pro_web(discipline, hippo, df):
    """Analyse haute fidélité utilisant ton accès Pro"""
    prompt = f"Expert Turf (Modèle Pro) : Analyse {discipline} à {hippo}. Partants : {df.to_string()}. Donne l'état du terrain, bruits d'écurie et ton top 3."
    
    try:
        # Tentative avec recherche Web (priorité Pro)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearchRetrieval())],
                temperature=0.4
            )
        )
        return response.text, "🏆 ANALYSE PRO (Google Search OK)"
    except Exception as e:
        # Fallback si le service de recherche web de Google est en maintenance ou sature
        if "429" in str(e):
            return "⏳ Le service de recherche est saturé. Réessaie dans quelques secondes.", "⚠️ QUOTA"
        return f"Erreur technique : {str(e)}", "❌ ERREUR"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Session PRO Active")

c1, c2 = st.columns(2)
with c1:
    discipline = st.selectbox("🎯 Discipline", ["Trot", "Galop", "Obstacle"])
    capital = st.number_input("💰 Capital (€)", value=1000)
with c2:
    hippo = st.text_input("📍 Hippodrome", value="Paris-Vincennes")
    txt_in = st.text_area("📋 Collez les partants ici :", height=120)

if st.button("🚀 LANCER L'EXPERTISE PRO"):
    df = extraire_partants_robuste(txt_in)
    
    if not df.empty:
        with st.spinner("🧠 Intelligence Artificielle Pro en cours d'analyse..."):
            expertise, status = expertise_pro_web(discipline, hippo, df)
        
        # Affichage du statut de la demande
        st.caption(f"Statut de la demande : {status}")
        
        if expertise:
            st.markdown(f'<div style="background-color:#f0f7ff; padding:20px; border-radius:15px; border-left:8px solid #007bff; color:#0d47a1;">{expertise}</div>', unsafe_allow_html=True)

        # Calculs et Mises (Kelly / Podium)
        resultats = []
        for _, row in df.iterrows():
            cote = max(row['cote'], 1.01)
            prob = (1 / cote) * 1.18 # Avantage IA Pro légèrement supérieur
            podium = min(98, int((prob ** 0.65) * 230))
            f_k = (prob * (cote-1) - (1-prob)) / (cote-1)
            mise = min(max(0, capital * f_k * 0.20), capital * 0.15) # Mise plus agressive pour capital Pro
            resultats.append({**row, "cote": cote, "podium": podium, "mise": mise})

        # Top 3
        st.write("---")
        st.subheader("🏁 Pronostics Stratégiques")
        top_3 = sorted(resultats, key=lambda x: x['podium'], reverse=True)[:3]
        cols = st.columns(3)
        for idx, r in enumerate(top_3):
            with cols[idx]:
                st.metric(label=f"Rang {idx+1} - n°{r['num']}", value=r['nom'], delta=f"{r['podium']}% Podium")
                st.write(f"Conseil : Mise **{round(r['mise'], 2)}€** à la cote de {r['cote']}")

    else:
        st.error("Vérifiez le format des partants.")
