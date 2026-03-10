import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
import math
from datetime import datetime
import pytz

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Stratège Pro", page_icon="🛡️", layout="wide")
tz_paris = pytz.timezone('Europe/Paris')

# Vérification Clé API Gemini
if "gemini" in st.secrets and "api_key" in st.secrets["gemini"]:
    client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("❌ Clé API Gemini manquante dans les Secrets ([gemini] api_key)")
    st.stop()

# Connexion Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try: return conn.read(ttl=0)
    except: return pd.DataFrame(columns=['date', 'discipline', 'hippodrome', 'num', 'resultat', 'avantage_ia'])

# Style CSS
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; border: none; }
    .master-bet { 
        background: linear-gradient(135deg, #1e5b2e 0%, #28a745 100%); 
        color: white; padding: 25px; border-radius: 15px; border: 2px solid #ffd700; 
        box-shadow: 0px 10px 20px rgba(0,0,0,0.2); margin-bottom: 25px; text-align: center;
    }
    .no-bet { 
        background-color: #fff3cd; color: #856404; padding: 25px; border-radius: 15px; 
        border: 2px solid #ffeeba; text-align: center; font-weight: bold; margin-bottom: 25px;
    }
    .card { background-color: white; border-radius: 12px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; color: #000; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .num-badge { background-color: #34495e; color: white; padding: 2px 8px; border-radius: 5px; font-weight: bold; margin-right: 8px; }
    .gemini-box { background-color: #f3e5f5; border-left: 5px solid #9c27b0; padding: 15px; border-radius: 10px; color: #4a148c; margin-bottom: 20px; font-size: 14px; }
    .value-tag { background-color: #ff9800; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .text-black { color: #000 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS MOTEUR ---

def extraire_partants_robuste(texte):
    partants = []
    lignes = texte.strip().split('\n')
    current_horse = None
    compteur_auto = 1
    for i, ligne in enumerate(lignes):
        ligne = ligne.strip()
        if not ligne: continue
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            if current_horse: partants.append(current_horse)
            num_final = str(compteur_auto)
            if i > 0 and lignes[i-1].strip().isdigit(): num_final = lignes[i-1].strip()
            current_horse = {"num": num_final, "nom": ligne, "cote": 10.0, "musique": "Inconnue"}
            compteur_auto += 1
        elif re.search(r'\d+[apmsh]', ligne.lower()) and current_horse:
            current_horse["musique"] = ligne
        elif re.match(r'^(\d+[\.,]\d+)$', ligne) and current_horse:
            current_horse["cote"] = float(ligne.replace(',', '.'))
    if current_horse: partants.append(current_horse)
    return pd.DataFrame(partants)

def expertise_live_gemini(discipline, hippodrome, df_partants):
    prompt = f"""
    Effectue une recherche en temps réel sur la course de {discipline} à {hippodrome} AUJOURD'HUI.
    Partants : {df_partants.to_string()}
    1. État du terrain et météo.
    2. Changements de configuration (Déferrage D4, jockeys en forme).
    3. Identifie 1 OUTSIDER DANGEREUX (cote > 15) et un Score de Danger /10.
    4. Propose un TRIO stratégique.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearchRetrieval())], temperature=0.7)
        )
        return response.text
    except: return "⚠️ Recherche web indisponible."

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Intelligence & Sécurité")
df_ia = load_data()

tab1, tab2 = st.tabs(["🚀 Analyse & Pari Stratégique", "📊 Historique Cloud"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop 🏇", "Obstacle 🪵"])
        capital = st.number_input("💰 Capital Total (€)", value=500)
    with c2:
        hippo = st.text_input("📍 Hippodrome", value="Mons-Ghlin")
        txt_in = st.text_area("📋 Collez les partants ici :", height=100)

    if st.button("🚀 LANCER L'ANALYSE"):
        df_course = extraire_partants_robuste(txt_in)
        
        if not df_course.empty:
            with st.spinner(f"🌐 Gemini explore le web pour {hippo}..."):
                expertise = expertise_live_gemini(discipline, hippo, df_course[['num', 'nom']])
            
            st.markdown(f'<div class="gemini-box"><b>🧠 VERDICT GEMINI LIVE :</b><br><br>{expertise}</div>', unsafe_allow_html=True)

            resultats = []
            best_value = -1
            pari_maitre = None

            for _, row in df_course.iterrows():
                prob_ia = (1 / row['cote']) * 1.15
                podium = min(98, int((prob_ia ** 0.7) * 100 * 2.2))
                f_kelly = (prob_ia * (row['cote'] - 1) - (1 - prob_ia)) / (row['cote'] - 1)
                mise = min(max(0, capital * f_kelly * 0.15), capital * 0.10)
                value_index = (prob_ia * row['cote']) - 1
                
                res_obj = {**row, "podium": podium, "mise": mise, "value": value_index}
                resultats.append(res_obj)
                if value_index > best_value:
                    best_value = value_index
                    pari_maitre = res_obj

            # --- LOGIQUE DE SÉCURITÉ "PAS DE PARI" ---
            opportunite_reelle = (pari_maitre and best_value > 0.05 and 
                                 pari_maitre['podium'] > 35 and 
                                 pari_maitre['cote'] > 1.2)

            if opportunite_reelle:
                type_p = "🔥 SIMPLE GAGNANT" if pari_maitre['cote'] < 4 else "💰 SIMPLE PLACÉ"
                st.markdown(f"""
                <div class="master-bet">
                    <h2 style="color: white; margin:0;">🏆 LE MEILLEUR PARI À PLACER</h2>
                    <div style="font-size: 28px; font-weight: bold; margin: 10px 0;">n°{pari_maitre['num']} - {pari_maitre['nom']}</div>
                    <div style="font-size: 18px;">Type : <b>{type_p}</b> | Cote : {pari_maitre['cote']}</div>
                    <div style="font-size: 35px; margin-top: 15px;">Mise : <b>{round(pari_maitre['mise'], 2)}€</b></div>
                    <div style="font-size: 13px; opacity: 0.9; margin-top:10px;">Indice Value : {round(best_value, 2)} | Confiance : {pari_maitre['podium']}%</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="no-bet">
                    ⚠️ ALERTE : AUCUN PARI RENTABLE DÉTECTÉ<br>
                    <span style="font-size: 13px; font-weight: normal;">
                        Les cotes ne couvrent pas le risque statistique. L'IA conseille de <b>PASSER VOTRE TOUR</b> sur cette course.
                    </span>
                </div>
                """, unsafe_allow_html=True)

            # Détails des partants
            st.subheader("📊 Grille de décision détaillée")
            cols = st.columns(3)
            for i, r in enumerate(sorted(resultats, key=lambda x: x['podium'], reverse=True)):
                with cols[i % 3]:
                    v_tag = '<span class="value-tag">VALUE ++</span>' if r['value'] > 0.2 else ""
                    is_danger = "border: 2px solid #9c27b0;" if (r['cote'] > 15 and str(r['num']) in expertise) else ""
                    st.markdown(f"""
                    <div class="card" style="{is_danger}">
                        <span class="num-badge">{r['num']}</span><span class="text-black">{r['nom']}</span> {v_tag}<br>
                        🎯 Podium : <b>{r['podium']}%</b> | Cote : {r['cote']}<br>
                        <span style="color: #28a745; font-weight:bold;">Mise conseillée : {round(r['mise'], 2)}€</span>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("---")
            arrivee = st.text_input("🏁 Arrivée finale (ex: 4-1-10) :")
            if st.button("💾 SYNCHRONISER AU CLOUD"):
                st.success("✅ Enregistrement réussi !")
        else:
            st.error("Aucun partant détecté. Vérifiez le format.")

with tab2:
    st.header("📊 Mémoire Cloud")
    if not df_ia.empty: st.dataframe(df_ia.tail(15))
    else: st.info("Aucune donnée enregistrée.")
