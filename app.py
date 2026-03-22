import streamlit as st
import pandas as pd
import re
import requests
import json
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : Pro Dashboard", page_icon="🏇", layout="wide")

# CSS : Fond Gris Clair, Texte Noir Intense, Bordures marquées
st.markdown("""
<style>
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; font-size: 20px !important; }
    [data-testid="stMetricLabel"] { color: #1a1a1a !important; font-weight: 700 !important; font-size: 15px !important; }
    
    /* Couleur du fond des bulles : GRIS CLAIR */
    [data-testid="stMetric"] { 
        background-color: #f0f2f6 !important; 
        padding: 15px !important; 
        border-radius: 12px !important; 
        border: 1px solid #cfd4da !important;
    }
    .stButton>button { width: 100%; border-radius: 20px; font-weight: bold; background-color: #000000; color: white; }
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
            # On construit "N° - NOM" pour l'IA
            identifiant = f"{num[0] if num else '?'} - {nom_cheval}"
            
            parts = ligne.split(nom_cheval)
            jockey = "Inconnu"
            if len(parts) > 1:
                suite = parts[1].strip()
                noms_propres = re.findall(r'^[A-Z][a-z]+', suite)
                if noms_propres:
                    jockey = noms_propres[0]

            data.append({
                "ID": identifiant,
                "Jockey": jockey,
                "Musique": " ".join(musique) if musique else "N/A"
            })
    return pd.DataFrame(data)

def simulation_ultra_pro(df, hippo, discipline, capital):
    partants_str = "\n".join([f"{row['ID']} (Jockey: {row['Jockey']} | Musique: {row['Musique']})" for _, row in df.iterrows()])
    
    prompt = f"""Expert Turf 2026. Hippodrome: {hippo} | Discipline: {discipline}.
    
    PARTANTS :
    {partants_str}

    MISSION :
    1. Détecte la distance et la météo live pour {hippo}.
    2. Calcule le TOP 5. Si un outsider (cote élevée/musique irrégulière) a une chance (>5%), INCLUS-LE dans le podium.
    3. Calcule la Probabilité de Victoire (%) exacte.

    RÉPONDS UNIQUEMENT EN JSON :
    {{
        "meteo": "☀️", "terrain": "Souple", "dist": "2850m",
        "podium": [
            {{"label": "🥇 1er", "nom": "N° - NOM", "prob": "32%", "info": "Favori solide"}},
            {{"label": "🥈 2ème", "nom": "N° - NOM", "prob": "18%", "info": "Régulier"}},
            {{"label": "🥉 3ème", "nom": "N° - NOM", "prob": "14%", "info": "Aime le terrain"}},
            {{"label": "🔥 OUTSIDER", "nom": "N° - NOM", "prob": "11%", "info": "Coup de poker"}},
            {{"label": "🏇 5ème", "nom": "N° - NOM", "prob": "7%", "info": "Bel engagement"}}
        ],
        "pari": "Couplé / Trio", "comb": "X - Y - Z", "mise": "20.00", "outsider_label": "NOM (N°X)"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

# --- 3. INTERFACE ---
st.title("🏇 TurfMaster 2.5 : Expert & Outsider")

with st.sidebar:
    st.header("⚙️ Configuration")
    hippo_input = st.text_input("Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot Attelé", "Trot Monté", "Plat", "Obstacles"])
    st.divider()
    capital = st.number_input("Capital (€)", value=1000)
    if st.button("🧹 Reset"): st.rerun()

st.markdown("### 📝 Partants (Format: N° NOM Jockey Musique)")
txt_in = st.text_area("", height=150, placeholder="Ex: 1 JIJI DOUZOU Raffin 1a 2a")

if st.button("🚀 ANALYSER LA COURSE"):
    df = extraire_data_expert(txt_in)
    if not df.empty:
        with st.spinner(f"📡 Calcul des probabilités pour {hippo_input}..."):
            raw = simulation_ultra_pro(df, hippo_input, discipline, capital)
            if raw:
                try:
                    res = json.loads(re.sub(r'```json\n|```', '', raw))
                    
                    # 1. PARAMÈTRES
                    st.markdown("### 📊 Conditions détectées")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Météo", res['meteo'])
                    m2.metric("Piste", res['terrain'])
                    m3.metric("Distance", res['dist'])

                    # 2. PODIUM (Gris Clair, Texte Noir)
                    st.markdown("### 🏆 Top 5 & Estimations")
                    cols = st.columns(5)
                    for i, p in enumerate(res['podium']):
                        with cols[i]:
                            st.metric(p['label'], p['nom'], p['prob'])
                            st.caption(f"💡 {p['info']}")

                    # 3. STRATÉGIE
                    st.divider()
                    l1, l2 = st.columns([2, 1])
                    with l1:
                        st.subheader("🎫 Ticket Platinum")
                        st.success(f"**Pari : {res['pari']}** | {res['comb']} | Mise : **{res['mise']} €**")
                    with l2:
                        st.subheader("🕵️ Outsider détecté")
                        st.warning(f"**{res['outsider_label']}**")
                except: st.error("Erreur de décodage. Réessayez.")
    else: st.error("Entrez des données valides.")

st.divider()
st.caption("Fonds Gris Clair #f0f2f6 | Texte Noir | Détection Outsider Intégrée")
