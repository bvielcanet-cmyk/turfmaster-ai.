import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏆", layout="wide")

# Initialisation du client avec ta clé
if "gemini" in st.secrets:
    client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("❌ Clé API manquante dans les Secrets Streamlit.")
    st.stop()

# --- 2. FONCTIONS DE POINTE ---

def extraire_partants(texte):
    partants = []
    texte = texte.replace('\xa0', ' ').replace('\t', ' ')
    lignes = texte.strip().split('\n')
    current = None
    compteur = 1
    for i, ligne in enumerate(lignes):
        ligne = ligne.strip()
        if not ligne: continue
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            if current: partants.append(current)
            num = lignes[i-1].strip() if i > 0 and lignes[i-1].strip().isdigit() else str(compteur)
            current = {"num": num, "nom": ligne, "cote": 20.0, "musique": "Inconnue"}
            compteur += 1
        else:
            cote_match = re.search(r'(\d+[\.,]\d+)', ligne)
            if cote_match and current:
                current["cote"] = float(cote_match.group(1).replace(',', '.'))
    if current: partants.append(current)
    return pd.DataFrame(partants)

def expertise_ia_pro(discipline, hippo, df):
    """Tentative sur 2.0 Flash, sinon Repli sur 1.5 Flash"""
    prompt = f"Expert Turf Pro : Analyse {discipline} à {hippo}. Partants : {df.to_string()}. Donne l'état du terrain et un pronostic Top 3."
    
    # On essaie d'abord le modèle le plus récent
    for model_to_test in ["gemini-2.0-flash", "gemini-1.5-flash"]:
        try:
            response = client.models.generate_content(
                model=model_to_test,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearchRetrieval())],
                    temperature=0.3
                )
            )
            return response.text, f"✅ OK ({model_to_test})"
        except Exception as e:
            # Si c'est une erreur de quota (429), on arrête
            if "429" in str(e):
                return None, "⚠️ Quota atteint (Attendez 1 minute)"
            # Sinon on continue vers le modèle suivant
            continue
            
    return None, "❌ Aucun modèle n'a répondu (Vérifiez votre clé API)"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Intelligence Stratégique")

c1, c2 = st.columns(2)
with c1:
    discipline = st.selectbox("🎯 Discipline", ["Trot", "Galop", "Obstacle"])
    capital = st.number_input("💰 Capital (€)", value=500)
with c2:
    hippo = st.text_input("📍 Hippodrome", value="Paris-Vincennes")
    txt_in = st.text_area("📋 Collez les partants ici :", height=100)

if st.button("🚀 LANCER L'ANALYSE"):
    df_course = extraire_partants(txt_in)
    
    if not df_course.empty:
        with st.spinner("🧠 Analyse en cours..."):
            expertise, status = expertise_ia_pro(discipline, hippo, df_course)
        
        st.caption(f"Statut : {status}")
        
        if expertise:
            st.markdown(f"""<div style="background-color:#f8f9fa; padding:20px; border-radius:15px; border-left:8px solid #28a745; color:#1a1a1a;">
                <b>Verdict de l'IA :</b><br>{expertise}</div>""", unsafe_allow_html=True)

            # --- CALCULS ---
            resultats = []
            for _, row in df_course.iterrows():
                cote = max(row['cote'], 1.01)
                prob = (1 / cote) * 1.15
                podium = min(98, int((prob ** 0.7) * 220))
                f_k = (prob * (cote-1) - (1-prob)) / (cote-1)
                mise = min(max(0, capital * f_k * 0.15), capital * 0.10)
                resultats.append({**row, "cote": cote, "podium": podium, "mise": mise})

            # Top 3
            st.write("---")
            st.subheader("🏁 Pronostics & Mises Kelly")
            top_3 = sorted(resultats, key=lambda x: x['podium'], reverse=True)[:3]
            cols = st.columns(3)
            for idx, r in enumerate(top_3):
                with cols[idx]:
                    st.metric(label=f"Rang {idx+1}", value=f"n°{r['num']} - {r['nom']}", delta=f"{r['podium']}%")
                    st.write(f"Mise suggérée : **{round(r['mise'], 2)}€**")
    else:
        st.error("Aucun cheval détecté. NOMS EN MAJUSCULES requis.")
