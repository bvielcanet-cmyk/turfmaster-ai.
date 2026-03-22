import streamlit as st
import pandas as pd
import re
import requests
import json
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : Ultra-Calculateur", page_icon="🧬", layout="wide")

# CSS : Noir profond et contraste haute visibilité
st.markdown("""
<style>
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; font-size: 22px !important; }
    [data-testid="stMetricLabel"] { color: #1a1a1a !important; font-weight: 600 !important; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 2px solid #000000; }
</style>
""", unsafe_allow_html=True)

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente.")
    st.stop()

# --- 2. FONCTIONS DE PARSING ---

def extraire_data_ultra(texte):
    lignes = texte.strip().split('\n')
    data = []
    for ligne in lignes:
        num = re.findall(r'^\d{1,2}', ligne.strip())
        nom = re.findall(r'\b[A-Z]{4,}\b', ligne)
        # On cherche maintenant le nom du Driver/Jockey (souvent après le nom du cheval)
        jockey = re.findall(r'(?<=\b[A-Z]{4,}\b\s)[A-Z][a-z]+', ligne)
        musique = re.findall(r'\b\d[admp]\b|\b[A-Z]D\b', ligne)
        if nom:
            data.append({
                "N°": num[0] if num else "?",
                "Nom": nom[0],
                "Jockey": jockey[0] if jockey else "Inconnu",
                "Musique": " ".join(musique) if musique else "N/A"
            })
    return pd.DataFrame(data)

def simulation_ultra_pro(df, hippo, discipline, dist, capital):
    partants_str = "\n".join([f"N°{row['N°']} {row['Nom']} (Jockey: {row['Jockey']} | Musique: {row['Musique']})" for _, row in df.iterrows()])
    
    prompt = f"""Expert Mathématique Turf 2026. Hippodrome: {hippo} | Distance: {dist}m | Discipline: {discipline}.
    
    PARTANTS À ANALYSER :
    {partants_str}

    ALGORITHME DE CALCUL :
    1. Score Musique (Forme : 40%) : 1a=+20, Da=-15, 4a=+5.
    2. Facteur Jockey/Entraîneur (20%) : Analyse la notoriété du nom indiqué.
    3. Aptitude Distance (20%) : Vérifie si le profil du cheval colle aux {dist}m.
    4. Fraîcheur (20%) : Analyse l'écart entre les dernières courses.

    RÉPONDS UNIQUEMENT EN JSON :
    {{
        "meteo": "☀️", "terrain": "Rapide",
        "podium": [
            {{"nom": "NOM1", "prob": "38%", "force": "Duo Jockey/Entraîneur"}},
            {{"nom": "NOM2", "prob": "24%", "force": "Forme ascendante"}},
            {{"nom": "NOM3", "prob": "14%", "force": "Spécialiste distance"}},
            {{"nom": "NOM4", "prob": "9%", "force": "Poids léger"}},
            {{"nom": "NOM5", "prob": "7%", "force": "Bel engagement"}}
        ],
        "pari": "Trio", "comb": "1 - 4 - X", "mise": "25.00", "outsider": "NOM (N°X) - Gros potentiel"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

# --- 3. INTERFACE ---
st.title("🧬 TurfMaster 2.5 : Intelligence Ultra-Calculatrice")

with st.sidebar:
    st.header("⚙️ Variables Course")
    hippo = st.text_input("Hippodrome", value="Vincennes")
    dist = st.number_input("Distance (mètres)", value=2700, step=100)
    discipline = st.selectbox("Discipline", ["Trot Attelé", "Trot Monté", "Plat", "Obstacles"])
    st.divider()
    capital = st.number_input("Capital (€)", value=1000)
    if st.button("🧹 Reset"): st.rerun()

st.markdown("### 📝 Saisie Expert (Format: N° NOM Jockey Musique)")
txt_in = st.text_area("", height=180, placeholder="Ex: 1 JIJI DOUZOU Raffin 1a 2a 4a")

if st.button("🚀 LANCER LE CALCUL HAUTE PRÉCISION", use_container_width=True):
    df = extraire_data_ultra(txt_in)
    if not df.empty:
        with st.spinner("🧬 Synchronisation des données et calcul des probabilités..."):
            raw = simulation_ultra_pro(df, hippo, discipline, dist, capital)
            if raw:
                try:
                    res = json.loads(re.sub(r'```json\n|```', '', raw))
                    
                    # 1. MÉTÉO & TERRAIN
                    st.markdown("### 📊 Analyse des Paramètres")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Météo", res['meteo'])
                    m2.metric("Piste", res['terrain'])
                    m3.metric("Distance", f"{dist}m")

                    # 2. PODIUM & POINTS FORTS
                    st.markdown("### 🏆 Top 5 Probabilités (Facteurs Clés)")
                    cols = st.columns(5)
                    medals = ["🥇", "🥈", "🥉", "4ème", "5ème"]
                    for i, p in enumerate(res['podium']):
                        with cols[i]:
                            st.metric(medals[i], p['nom'], p['prob'])
                            st.caption(f"💡 {p['force']}")

                    # 3. STRATÉGIE
                    st.divider()
                    l1, l2 = st.columns([2, 1])
                    with l1:
                        st.subheader("🎫 Ticket de Précision")
                        st.success(f"**Pari : {res['pari']}** | Combinaison : **{res['comb']}** | Mise : **{res['mise']} €**")
                    with l2:
                        st.subheader("🕵️ L'Analyse Outsider")
                        st.warning(f"**{res['outsider']}**")
                except: st.error("L'IA a rencontré une erreur de calcul. Réessayez.")
    else: st.error("Veuillez entrer des partants.")

st.divider()
st.caption("Version 2.5 Ultra | Calcul Pondéré Multi-Facteurs | Gemini Platinum 2026")
