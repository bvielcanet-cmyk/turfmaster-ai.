import streamlit as st
import pandas as pd  # Correction ici : pandas et non pd
import re
import requests
import json
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : Final Pro", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; font-size: 16px !important; }
    [data-testid="stMetricLabel"] { color: #1a1a1a !important; font-weight: 700 !important; font-size: 13px !important; margin-bottom: -8px !important; }
    [data-testid="stMetric"] { background-color: #bdc3c7 !important; padding: 8px 10px !important; border-radius: 8px !important; border: 1px solid #7f8c8d !important; }
    .stButton>button { background-color: #000000; color: white; border-radius: 12px; font-weight: bold; }
    .risk-low { color: #27ae60; font-weight: bold; }
    .risk-med { color: #f39c12; font-weight: bold; }
    .risk-high { color: #e74c3c; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Configurez votre API KEY dans les Secrets.")
    st.stop()

# --- 2. FONCTIONS DE CALCUL ---

def extraire_data_pro(texte):
    lignes = texte.strip().split('\n')
    data = []
    for ligne in lignes:
        num_match = re.search(r'^(\d{1,2})', ligne.strip())
        nom_match = re.findall(r'[A-Z]{4,}', ligne)
        fer = re.findall(r'\bD4\b|\bDP\b|\bDA\b', ligne)
        musique = re.findall(r'\b\d[admp]\b|\b[A-Z]D\b', ligne)
        
        if nom_match:
            numero = num_match.group(1) if num_match else "?"
            data.append({
                "FULL_ID": f"{numero} - {nom_match[0]}",
                "NUM": numero,
                "Info": f"{fer[0] if fer else 'F'} | {' '.join(musique) if musique else 'N/A'}"
            })
    return pd.DataFrame(data)

def simulation_performance_max(df, hippo, discipline, capital, profil):
    partants_str = "\n".join([f"{row['FULL_ID']} ({row['Info']})" for _, row in df.iterrows()])
    
    prompt = f"""Expert Turf 2026. Hippodrome: {hippo} | Discipline: {discipline}.
    
    PARTANTS (Numéros Réels fournis) : 
    {partants_str}

    MISSION :
    1. Détermine Météo/Distance pour {hippo}.
    2. Calcule le TOP 5 Probabilités. 
    3. Analyse obligatoirement si un Outsider (🔥) a un potentiel (>5% proba) et place-le dans le podium.
    4. Génère un ticket avec UNIQUEMENT les numéros des chevaux.

    RÉPONDS EN JSON STRICT :
    {{
        "m": "☀️", "d": "2700m", "r": "Modéré", "ordre": "Num - Num - Num",
        "podium": [
            {{"n": "NUM - NOM", "p": "38%"}},
            {{"n": "NUM - NOM", "p": "22%"}},
            {{"n": "NUM - NOM", "p": "15%"}},
            {{"n": "NUM - NOM", "p": "11%"}},
            {{"n": "NUM - NOM", "p": "8%"}}
        ],
        "pari_nom": "Trio Combiné",
        "pari_nums": "12 - 4 - 7 - 1",
        "mise": "20.00", 
        "gain": "+35€"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    
    try:
        response = requests.post(url, json=payload, timeout=25)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        return None
    except: return None

# --- 3. INTERFACE ---
st.title("🚀 TurfMaster 2.5 : Ultimate Investor")

with st.sidebar:
    hippo_input = st.text_input("Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot", "Plat", "Obstacles"])
    st.divider()
    capital = st.number_input("Capital (€)", value=1000)
    profil = st.select_slider("Profil de Risque", ["Prudent", "Équilibré", "Offensif"], value="Équilibré")
    if st.button("🧹 Reset"): st.rerun()

txt_in = st.text_area("📋 Collez ici (ex: 12 FAKIR D4 1a)", height=150)

if st.button("⚡ GÉNÉRER LE TICKET GAGNANT"):
    df = extraire_data_pro(txt_in)
    if not df.empty:
        with st.spinner("🧪 Analyse des cotes et détection d'outsider..."):
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

                    # 2. PODIUM (Numéro - Nom)
                    st.divider()
                    cols = st.columns(5)
                    meds = ["🥇 1er", "🥈 2ème", "🥉 3ème", "🔥 OUT", "🏇 5ème"]
                    for i, p in enumerate(res['podium']):
                        cols[i].metric(meds[i], p['n'], p['p'])

                    # 3. TICKET FINAL (Numéros inclus)
                    st.divider()
                    l1, l2 = st.columns([2, 1])
                    with l1:
                        st.success(f"🎫 **{res['pari_nom']}** | Chevaux : **{res['pari_nums']}** | Mise : **{res['mise']} €**")
                    with l2:
                        st.metric("Gain Net Est.", res['gain'])

                except: st.error("Erreur d'analyse. Réessayez l'envoi.")
    else: st.error("Veuillez saisir des partants (ex: 12 NOM).")

st.divider()
st.caption("Correction Pandas appliquée | Numéros Réels | Outsider 🔥 | Fond #bdc3c7")
