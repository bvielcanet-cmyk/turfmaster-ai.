import streamlit as st
import pandas as pd
import re
import requests
import json
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : Performance Max", page_icon="🚀", layout="wide")

# CSS : Noir profond, Fond Gris Moyen, Contrastes optimisés
st.markdown("""
<style>
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; font-size: 16px !important; }
    [data-testid="stMetricLabel"] { color: #1a1a1a !important; font-weight: 700 !important; font-size: 13px !important; margin-bottom: -8px !important; }
    [data-testid="stMetric"] { 
        background-color: #bdc3c7 !important; 
        padding: 8px 10px !important; 
        border-radius: 8px !important; 
        border: 1px solid #7f8c8d !important;
    }
    .stButton>button { background-color: #000000; color: white; border-radius: 12px; font-weight: bold; }
    .risk-low { color: #27ae60; font-weight: bold; }
    .risk-med { color: #f39c12; font-weight: bold; }
    .risk-high { color: #e74c3c; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Configurez votre API KEY.")
    st.stop()

# --- 2. FONCTIONS DE CALCUL ---

def extraire_data_pro(texte):
    lignes = texte.strip().split('\n')
    data = []
    for ligne in lignes:
        num = re.findall(r'^\d{1,2}', ligne.strip())
        noms_trouves = re.findall(r'[A-Z]{4,}', ligne)
        # Détection Ferrure (D4, DP, DA)
        fer = re.findall(r'\bD4\b|\bDP\b|\bDA\b', ligne)
        musique = re.findall(r'\b\d[admp]\b|\b[A-Z]D\b', ligne)
        if noms_trouves:
            nom_cheval = noms_trouves[0]
            numero = num[0] if num else "?"
            data.append({
                "ID": f"{numero} - {nom_cheval}",
                "Info": f"{fer[0] if fer else 'Ferré'} | { ' '.join(musique) if musique else 'N/A'}"
            })
    return pd.DataFrame(data)

def simulation_performance_max(df, hippo, discipline, capital, profil):
    partants_str = "\n".join([f"{row['ID']} ({row['Info']})" for _, row in df.iterrows()])
    
    prompt = f"""Expert Turf 2026 Algorithmique. 
    Lieu : {hippo} | Discipline : {discipline} | Capital : {capital}€ | Profil : {profil}
    
    PARTANTS : 
    {partants_str}

    ALGORITHME DE PONDÉRATION :
    - Bonus Ferrure D4 : +15% probabilité.
    - Malus Rentrée (>90j) : -10% probabilité.
    - Bonus Forme (1a, 2a) : +20% probabilité.
    - Malus Fautes (Da, Dp) : -15% probabilité au trot.

    MISSION :
    1. Détermine Météo/Distance pour {hippo}.
    2. Calcule le TOP 5 (N° - NOM | Probabilité %).
    3. Calcule la Mise OPTIMALE selon le profil {profil}.

    RÉPONDS EN JSON STRICT :
    {{
        "m": "☀️", "d": "2700m", "r": "Modéré", "ordre": "12-4-7-1-9",
        "podium": [
            {{"n": "N° - NOM", "p": "38%"}},
            {{"n": "N° - NOM", "p": "22%"}},
            {{"n": "N° - NOM", "p": "15%"}},
            {{"n": "N° - NOM", "p": "11%"}},
            {{"n": "N° - NOM", "p": "8%"}}
        ],
        "pari": "Couplé Gagnant", "mise": "25.00", "gain_estime": "+45€"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    
    try:
        response = requests.post(url, json=payload, timeout=25)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

# --- 3. INTERFACE ---
st.title("🚀 TurfMaster 2.5 : Performance Max")

with st.sidebar:
    hippo_input = st.text_input("Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot", "Plat", "Obstacles"])
    st.divider()
    capital = st.number_input("Capital (€)", value=1000)
    profil = st.select_slider("Profil", ["Prudent", "Équilibré", "Offensif"], value="Équilibré")
    if st.button("🧹 Reset"): st.rerun()

txt_in = st.text_area("📋 Partants (N° NOM Ferrure Musique)", height=150, placeholder="12 FAKIR D4 1a 2a...")

if st.button("⚡ ANALYSE HAUTE PERFORMANCE"):
    df = extraire_data_pro(txt_in)
    if not df.empty:
        with st.spinner("🧪 Traitement algorithmique..."):
            raw = simulation_performance_max(df, hippo_input, discipline, capital, profil)
            if raw:
                try:
                    res = json.loads(re.sub(r'```json\n|```', '', raw))
                    st.divider()
                    
                    # 1. BANDEAU INFO
                    c1, c2, c3 = st.columns([1, 1, 2])
                    color = "risk-low" if res['r'] == "Faible" else ("risk-med" if res['r'] == "Modéré" else "risk-high")
                    c1.markdown(f"Risque : <span class='{color}'>{res['r']}</span>", unsafe_allow_html=True)
                    c2.write(f"📍 {res['d']} | {res['m']}")
                    c3.info(f"🏁 Ordre : **{res['ordre']}**")

                    # 2. PODIUM COMPACT
                    st.divider()
                    cols = st.columns(5)
                    meds = ["🥇", "🥈", "🥉", "🔥", "🏇"]
                    for i, p in enumerate(res['podium']):
                        cols[i].metric(meds[i], p['n'], p['p'])

                    # 3. TICKET FINAL
                    st.divider()
                    l1, l2 = st.columns([2, 1])
                    l1.success(f"🎫 **{res['pari']}** | Mise : **{res['mise']} €**")
                    l2.metric("Gain Net Est.", res['gain_estime'])

                except: st.error("L'IA a besoin de données plus claires. Réessayez.")
    else: st.error("Saisissez des partants.")

st.divider()
st.caption("Pondération Ferrure & Fraîcheur activée | Gemini 2.5 Performance")
