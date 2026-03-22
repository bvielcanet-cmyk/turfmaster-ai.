import streamlit as st
import pandas as pd
import re
import requests
import json
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : Compact Pro", page_icon="📈", layout="wide")

# CSS : Bulles Compactes, Fond Gris Moyen, Texte Noir
st.markdown("""
<style>
    /* Valeur principale (Nom du cheval) */
    [data-testid="stMetricValue"] { 
        color: #000000 !important; 
        font-weight: 800 !important; 
        font-size: 16px !important; 
    }
    /* Libellé (🥇 1er, etc.) */
    [data-testid="stMetricLabel"] { 
        color: #1a1a1a !important; 
        font-weight: 700 !important; 
        font-size: 13px !important;
        margin-bottom: -10px !important;
    }
    /* Conteneur de la bulle : GRIS MOYEN */
    [data-testid="stMetric"] { 
        background-color: #bdc3c7 !important; 
        padding: 8px 12px !important; 
        border-radius: 8px !important; 
        border: 1px solid #7f8c8d !important;
    }
    /* Réduction de l'espace entre les colonnes */
    [data-testid="column"] { padding: 0px 5px !important; }
    .stButton>button { background-color: #000000; color: white; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente.")
    st.stop()

# --- 2. FONCTIONS DE PARSING ---

def extraire_data_expert(texte):
    lignes = texte.strip().split('\n')
    data = []
    for ligne in lignes:
        num = re.findall(r'^\d{1,2}', ligne.strip())
        noms_trouves = re.findall(r'[A-Z]{4,}', ligne)
        musique = re.findall(r'\b\d[admp]\b|\b[A-Z]D\b', ligne)
        if noms_trouves:
            nom_cheval = noms_trouves[0]
            numero = num[0] if num else "?"
            data.append({
                "ID": f"{numero} - {nom_cheval}", # Format N° - NOM
                "Musique": " ".join(musique) if musique else "N/A"
            })
    return pd.DataFrame(data)

def simulation_investor(df, hippo, discipline, capital):
    partants_str = "\n".join([f"{row['ID']} ({row['Musique']})" for _, row in df.iterrows()])
    
    prompt = f"""Expert Turf 2026. Hippodrome: {hippo} | Discipline: {discipline}.
    
    PARTANTS (Format N° - NOM) :
    {partants_str}

    MISSION :
    1. Analyse météo et distance pour {hippo}.
    2. Calcule le TOP 5 avec Probabilités (%).
    3. Garde impérativement le format "N° - NOM" partout.

    RÉPONDS UNIQUEMENT EN JSON :
    {{
        "meteo": "☀️", "dist": "2700m", "verdict": "VALABLE",
        "podium": [
            {{"label": "🥇 1er", "nom": "N° - NOM", "prob": "35%"}},
            {{"label": "🥈 2ème", "nom": "N° - NOM", "prob": "20%"}},
            {{"label": "🥉 3ème", "nom": "N° - NOM", "prob": "15%"}},
            {{"label": "🔥 OUT", "nom": "N° - NOM", "prob": "12%"}},
            {{"label": "🏇 5ème", "nom": "N° - NOM", "prob": "8%"}}
        ],
        "pari": "Couplé Gagnant", "comb": "N° - N°", "mise": "15.00"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    
    try:
        response = requests.post(url, json=payload, timeout=25)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

# --- 3. INTERFACE ---
st.title("🏇 TurfMaster 2.5 : Compact Investor")

with st.sidebar:
    st.header("⚙️ Settings")
    hippo_input = st.text_input("Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot", "Plat", "Obstacles"])
    capital = st.number_input("Capital (€)", value=1000)
    if st.button("🧹 Reset"): st.rerun()

txt_in = st.text_area("📝 Liste des Partants (N° NOM Musique)", height=150, placeholder="12 FAKIR 1a 2a...")

if st.button("🚀 ANALYSER LA COURSE"):
    df = extraire_data_expert(txt_in)
    if not df.empty:
        with st.spinner("⏳"):
            raw = simulation_investor(df, hippo_input, discipline, capital)
            if raw:
                try:
                    res = json.loads(re.sub(r'```json\n|```', '', raw))
                    
                    # 1. PARAMÈTRES (Compact)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Ciel", res['meteo'])
                    m2.metric("Piste", res['dist'])
                    m3.metric("Verdict", res['verdict'])

                    # 2. PODIUM COMPACT (Gris Moyen, Texte Noir)
                    st.divider()
                    cols = st.columns(5)
                    for i, p in enumerate(res['podium']):
                        cols[i].metric(p['label'], p['nom'], p['prob'])

                    # 3. TICKET
                    st.divider()
                    st.success(f"**{res['pari']}** | {res['comb']} | Mise : **{res['mise']} €**")
                except: st.error("Erreur. Réessayez.")
    else: st.error("Saisissez des partants.")

st.divider()
st.caption("Bulles Compactes #bdc3c7 | Texte Noir | N° Inclus")
