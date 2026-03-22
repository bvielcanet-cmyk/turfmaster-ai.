import streamlit as st
import pandas as pd
import re
import requests
import json
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : Ultra-Calculateur", page_icon="🧬", layout="wide")

# CSS : Noir profond et contraste haute visibilité (Corrigé pour lisibilité)
st.markdown("""
<style>
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; font-size: 22px !important; }
    [data-testid="stMetricLabel"] { color: #1a1a1a !important; font-weight: 600 !important; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 2px solid #000000; }
    .stButton>button { width: 100%; border-radius: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente dans les Secrets.")
    st.stop()

# --- 2. FONCTIONS DE PARSING (CORRIGÉE SANS LOOK-BEHIND) ---

def extraire_data_ultra(texte):
    lignes = texte.strip().split('\n')
    data = []
    for ligne in lignes:
        # 1. Numéro
        num = re.findall(r'^\d{1,2}', ligne.strip())
        # 2. Nom du cheval (MAJUSCULES de 4+ lettres)
        noms_trouves = re.findall(r'[A-Z]{4,}', ligne)
        # 3. Musique
        musique = re.findall(r'\b\d[admp]\b|\b[A-Z]D\b', ligne)
        
        if noms_trouves:
            nom_cheval = noms_trouves[0]
            # 4. Extraction Jockey (Vérification après le nom)
            parts = ligne.split(nom_cheval)
            jockey = "Inconnu"
            if len(parts) > 1:
                suite = parts[1].strip()
                noms_propres = re.findall(r'^[A-Z][a-z]+', suite)
                if noms_propres:
                    jockey = noms_propres[0]

            data.append({
                "N°": num[0] if num else "?",
                "Nom": nom_cheval,
                "Jockey": jockey,
                "Musique": " ".join(musique) if musique else "N/A"
            })
    return pd.DataFrame(data)

def simulation_ultra_pro(df, hippo, discipline, capital):
    partants_str = "\n".join([f"N°{row['N°']} {row['Nom']} (Jockey: {row['Jockey']} | Musique: {row['Musique']})" for _, row in df.iterrows()])
    
    prompt = f"""Expert Mathématique Turf 2026. 
    HIPPODROME : {hippo} | DISCIPLINE : {discipline}
    
    MISSION :
    1. Identifie AUTOMATIQUEMENT la distance classique et le profil de piste pour {hippo}.
    2. Analyse ces partants :
    {partants_str}

    ALGORITHME :
    - Score Forme (40%) | Duo Jockey/Entraîneur (20%) | Aptitude Tracé (20%) | Fraîcheur (20%).

    RÉPONDS UNIQUEMENT EN JSON :
    {{
        "meteo": "☀️", "terrain": "Rapide", "dist_detectee": "2700m",
        "podium": [
            {{"nom": "NOM1", "prob": "38%", "force": "Duo de choc"}},
            {{"nom": "NOM2", "prob": "24%", "force": "Forme"}},
            {{"nom": "NOM3", "prob": "14%", "force": "Distance"}},
            {{"nom": "NOM4", "prob": "9%", "force": "Poids"}},
            {{"nom": "NOM5", "prob": "7%", "force": "Engagement"}}
        ],
        "pari": "Trio", "comb": "1-4-X", "mise": "25.00", "outsider": "NOM (N°X)"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

# --- 3. INTERFACE ---
st.title("🧬 TurfMaster 2.5 : Intelligence Autonome")

with st.sidebar:
    st.header("⚙️ Configuration")
    hippo_input = st.text_input("Nom de l'Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot Attelé", "Trot Monté", "Plat", "Obstacles"])
    st.divider()
    capital = st.number_input("Capital (€)", value=1000)
    if st.button("🧹 Reset"):
        st.rerun()

st.markdown("### 📝 Saisie Rapide (N° NOM Jockey Musique)")
txt_in = st.text_area("", height=180, placeholder="Ex: 1 JIJI DOUZOU Raffin 1a 2a 4a")

if st.button("🚀 ANALYSER LA COURSE"):
    df = extraire_data_ultra(txt_in)
    if not df.empty:
        with st.spinner(f"🧬 Recherche du tracé de {hippo_input} et calcul..."):
            raw = simulation_ultra_pro(df, hippo_input, discipline, capital)
            if raw:
                try:
                    # Nettoyage JSON
                    res = json.loads(re.sub(r'```json\n|```', '', raw))
                    
                    # 1. PARAMÈTRES DÉTECTÉS
                    st.markdown("### 📊 Analyse Automatique")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Météo", res['meteo'])
                    m2.metric("Piste", res['terrain'])
                    m3.metric("Distance Détectée", res['dist_detectee'])

                    # 2. PODIUM
                    st.markdown("### 🏆 Probabilités de Victoire")
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
                        st.subheader("🎫 Ticket Platinum")
                        st.success(f"**Pari : {res['pari']}** | Combinaison : **{res['comb']}** | Mise : **{res['mise']} €**")
                    with l2:
                        st.subheader("🕵️ L'Outsider")
                        st.warning(f"**{res['outsider']}**")
                except: st.error("Erreur de décodage. Réessayez l'analyse.")
    else: st.error("Veuillez entrer au moins un partant valide.")

st.divider()
st.caption("Auto-détection de distance activée | Moteur Gemini 2.5 Flash")
