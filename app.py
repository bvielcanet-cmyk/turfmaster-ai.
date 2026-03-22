import streamlit as st
import pandas as pd
import re
import requests
import json
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : Platinum Dashboard", page_icon="🏇", layout="wide")

# Personnalisation CSS pour rendre l'interface plus ludique
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #d1d1d1;
    }
    .stDataFrame {
        border-radius: 10px;
    }
    .prono-win {
        color: #ff4b4b;
        font-weight: bold;
        font-size: 24px;
    }
</style>
""", unsafe_allow_html=True)

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Configurez la clé API dans les Secrets.")
    st.stop()

# --- 2. FONCTIONS DE CALCUL & RECHERCHE ---

def extraire_data_expert(texte):
    lignes = texte.strip().split('\n')
    data = []
    for ligne in lignes:
        numero = re.findall(r'^\d{1,2}', ligne.strip())
        nom = re.findall(r'\b[A-Z]{4,}\b', ligne)
        ferrure = re.findall(r'\bD4\b|\bDP\b|\bDA\b', ligne)
        musique = re.findall(r'\b\d[admp]\b|\b[A-Z]D\b', ligne)
        if nom:
            data.append({
                "N°": numero[0] if numero else "?",
                "Nom": nom[0],
                "Fer": ferrure[0] if ferrure else "F",
                "Musique": " ".join(musique) if musique else "N/A"
            })
    return pd.DataFrame(data)

def analyse_platinum_dashboard(df, nom_hippo, discipline, capital):
    liste_chevaux = "\n".join([f"N°{row['N°']} {row['Nom']} ({row['Fer']} | {row['Musique']})" for _, row in df.iterrows()])
    
    # Prompt forçant une sortie JSON structurée pour l'interface graphique
    prompt = f"""Expert Turf Platinum 2026. Analyse Stratégique pour {nom_hippo} ({discipline}).
    
    DONNÉES :
    {liste_chevaux}

    MISSION : 
    1. Analyse flash pour {nom_hippo}.
    2. Identifie Météo, Température (°C), État du Terrain.
    3. Calcule l'Ordre d'Arrivée (Noms des 5 premiers).
    4. Calcule Score de Performance (0-100) pour chaque partant.
    5. Détermine le Pari Conseillé (ex: Trio combiné, Simple Gagnant).
    6. Calcule la Mise Kelly Totale suggérée sur {capital}€.

    Réponds UNIQUEMENT avec un objet JSON strictement formaté comme suit :
    {{
        "meteo_icon": "☀️",
        "meteo_desc": "Ensoleillé",
        "temp": "18",
        "terrain": "Bon",
        "podium_noms": ["NOM1", "NOM2", "NOM3", "NOM4", "NOM5"],
        "pari_type": "Trio Combiné",
        "pari_comb": "1 - 4 - 7 - 12",
        "mise_suggeree": "45.00",
        "outsider": "NOM (N°X)"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        return None
    except Exception as e:
        return None

# --- 3. INTERFACE ---
st.title("🏇 TurfMaster 2.5 : Platinum Dashboard")
st.caption(f"Analyse algorithmique du {datetime.now().strftime('%d/%m/%Y')} - Moteur Gemini 2.5 Flash")

if 'input_text' not in st.session_state:
    st.session_state['input_text'] = ""

with st.sidebar:
    st.header("⚙️ Configuration")
    nom_hippo = st.text_input("Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot", "Plat", "Obstacles"])
    st.divider()
    capital = st.number_input("Capital (€)", value=1000)
    if st.button("🧹 Vider les données"):
        st.session_state['input_text'] = ""
        st.rerun()

# --- ZONE DE SAISIE ---
st.markdown("### 📋 1. Saisie des Partants")
txt_in = st.text_area("Collez vos données ici (Num Nom Fer Musique) :", 
                      value=st.session_state['input_text'], 
                      height=200, 
                      placeholder="1 JIJI DOUZOU D4 1a 2a...")
st.session_state['input_text'] = txt_in

# --- BOUTON DE LANCEMENT ---
if st.button("🚀 LANCER L'ANALYSE PLATINUM", use_container_width=True):
    df = extraire_data_expert(txt_in)
    if not df.empty:
        with st.spinner(f"🧠 L'algorithme analyse {nom_hippo}..."):
            resultat_raw = analyse_platinum_dashboard(df, nom_hippo, discipline, capital)
            
            if resultat_raw:
                # Nettoyage et parsing du JSON
                try:
                    # L'IA met parfois des backticks autour du JSON
                    cleaned_json = re.sub(r'```json\n|```', '', resultat_raw)
                    res = json.loads(cleaned_json)
                    
                    st.success("🏁 Analyse Terminée !")
                    st.divider()
                    
                    # --- AFFICHAGE LUDIQUE ---
                    
                    # 1. Barre Météo
                    st.markdown("### 🌦️ Météo & Terrain")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Météo", res['meteo_icon'], res['meteo_desc'], delta_color="off")
                    with col2:
                        st.metric("Température", f"{res['temp']} °C")
                    with col3:
                        st.metric("État du Terrain", res['terrain'])
                    
                    st.divider()
                    
                    # 2. Le Podium
                    st.markdown("### 🏆 Podium Probable")
                    c1, c2, c3, c4, c5 = st.columns(5)
                    with c1: st.metric("🥇 1er", res['podium_noms'][0], help="C'est le favori de l'IA")
                    with c2: st.metric("🥈 2ème", res['podium_noms'][1])
                    with c3: st.metric("🥉 3ème", res['podium_noms'][2])
                    with c4: st.metric("4ème", res['podium_noms'][3])
                    with c5: st.metric("5ème", res['podium_noms'][4])
                    
                    st.divider()
                    
                    # 3. Le Ticket & L'Outsider
                    cl1, cl2 = st.columns([2, 1])
                    
                    with cl1:
                        st.subheader("🎫 Votre Ticket Stratégique")
                        st.success(f"""
                        - **Pari conseillé** : **{res['pari_type']}**
                        - **Combinaison** : **{res['pari_comb']}**
                        - **Mise recommandée** : **{res['mise_suggeree']} €**
                        """)
                    
                    with cl2:
                        st.subheader("🕵️ L'Outsider Spéculatif")
                        st.warning(f"""
                        **{res['outsider']}**
                        \nIl a une forte aptitude aux conditions actuelles !
                        """)

                except Exception as e:
                    st.error("Erreur de formatage du résultat. Réessayez.")
                    with st.expander("Voir la réponse brute"):
                        st.write(resultat_raw)
            else:
                st.error("L'IA n'a pas répondu. Timeout probable. Réessayez.")
    else:
        st.error("Aucune donnée détectée.")

st.divider()
st.caption("Version 2.5 : Dashboard Visuel | Zéro Simulation lourde.")
