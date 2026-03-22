import streamlit as st
import pandas as pd
import re
import requests
import json
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : Investor Edition", page_icon="📈", layout="wide")

# CSS : Noir profond, Fond Gris, Boutons Gold
st.markdown("""
<style>
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #1a1a1a !important; font-weight: 700; }
    [data-testid="stMetric"] { background-color: #f0f2f6 !important; border-radius: 10px; border: 1px solid #bdc3c7; }
    .stButton>button { background-color: #d4af37; color: black; border: none; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente.")
    st.stop()

# --- 2. FONCTIONS ---

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
            data.append({"ID": f"{numero} - {nom_cheval}", "Musique": " ".join(musique)})
    return pd.DataFrame(data)

def simulation_investor(df, hippo, discipline, capital, profil_risque):
    partants_str = "\n".join([f"{row['ID']} ({row['Musique']})" for _, row in df.iterrows()])
    
    prompt = f"""Expert Mathématique Turf 2026. Hippodrome: {hippo} | Discipline: {discipline}.
    CAPITAL : {capital}€ | PROFIL : {profil_risque}
    
    PARTANTS :
    {partants_str}

    LOGIQUE D'INVESTISSEMENT :
    1. Calcule la probabilité de victoire (%) réelle.
    2. Applique le filtre "Value Bet" (Probabilité vs Risque).
    3. Si le risque est trop élevé (>70% d'incertitude), suggère de NE PAS PARIER.

    RÉPONDS UNIQUEMENT EN JSON :
    {{
        "meteo": "☀️", "dist": "2700m", "verdict": "VALABLE / RISQUÉ / À ÉVITER",
        "podium": [
            {{"label": "🥇 1er", "nom": "N° - NOM", "prob": "35%"}},
            {{"label": "🥈 2ème", "nom": "N° - NOM", "prob": "20%"}},
            {{"label": "🥉 3ème", "nom": "N° - NOM", "prob": "15%"}},
            {{"label": "🔥 OUTSIDER", "nom": "N° - NOM", "prob": "11%"}},
            {{"label": "🏇 5ème", "nom": "N° - NOM", "prob": "8%"}}
        ],
        "pari": "Type de pari", "comb": "X - Y", "mise": "15.00", "roi_estime": "+12%"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

# --- 3. INTERFACE ---
st.title("📈 TurfMaster 2.5 : Investor Edition")

with st.sidebar:
    st.header("⚖️ Stratégie")
    hippo_input = st.text_input("Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot Attelé", "Plat", "Obstacles"])
    capital = st.number_input("Bankroll (€)", value=1000)
    profil = st.select_slider("Profil de Risque", options=["Prudent", "Équilibré", "Offensif"], value="Équilibré")
    if st.button("🧹 Reset"): st.rerun()

st.markdown("### 📝 Liste des Partants")
txt_in = st.text_area("", height=150, placeholder="Ex: 12 FAKIR 1a 2a")

if st.button("🚀 ANALYSE DE RENTABILITÉ"):
    df = extraire_data_expert(txt_in)
    if not df.empty:
        with st.spinner("⏳ Calcul du ROI théorique..."):
            raw = simulation_investor(df, hippo_input, discipline, capital, profil)
            if raw:
                try:
                    res = json.loads(re.sub(r'```json\n|```', '', raw))
                    
                    st.divider()
                    # 1. VERDICT & ROI
                    st.markdown(f"### 🛡️ Verdict : **{res['verdict']}**")
                    v1, v2, v3 = st.columns(3)
                    v1.metric("Distance", res['dist'])
                    v2.metric("Météo", res['meteo'])
                    v3.metric("ROI Estimé", res['roi_estime'], delta=res['roi_estime'])

                    # 2. PODIUM (N° - NOM)
                    st.markdown("### 🏆 Top 5 Probabilités")
                    cols = st.columns(5)
                    for i, p in enumerate(res['podium']):
                        cols[i].metric(p['label'], p['nom'], p['prob'])

                    # 3. TICKET
                    st.divider()
                    st.subheader("🎫 Ticket d'Investissement")
                    if res['verdict'] == "À ÉVITER":
                        st.error("⚠️ L'IA déconseille de parier sur cette course (Trop d'incertitude).")
                    else:
                        st.success(f"**Pari : {res['pari']}** | {res['comb']} | Mise : **{res['mise']} €** (Kelly optimisé)")
                except: st.error("Erreur d'analyse. Réessayez.")
    else: st.error("Saisissez des partants.")

st.divider()
st.caption("Filtre Value Bet & Kelly Quarter | Gemini 2.5 Platinum")
