import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
import time
import pytz

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Expert", page_icon="🏇", layout="wide")

if "gemini" in st.secrets:
    client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("❌ Clé API manquante dans les Secrets.")
    st.stop()

# Styles CSS
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; background-color: #28a745; color: white; font-weight: bold; }
    .master-bet { background: linear-gradient(135deg, #1e5b2e 0%, #28a745 100%); color: white; padding: 20px; border-radius: 15px; text-align: center; border: 2px solid #ffd700; }
    .gemini-box { background-color: #f3e5f5; border-left: 5px solid #9c27b0; padding: 15px; border-radius: 10px; color: #4a148c; }
    .card { background-color: white; border-radius: 12px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; color: black; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .num-badge { background-color: #34495e; color: white; padding: 2px 8px; border-radius: 5px; font-weight: bold; margin-right: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE MOTEUR AVEC GESTION DE QUOTA ---

def extraire_partants(texte):
    partants = []
    texte = texte.replace('\xa0', ' ').replace('\t', ' ')
    lignes = texte.strip().split('\n')
    current = None
    for i, ligne in enumerate(lignes):
        ligne = ligne.strip()
        if not ligne: continue
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            if current: partants.append(current)
            num = lignes[i-1].strip() if i > 0 and lignes[i-1].strip().isdigit() else "1"
            current = {"num": num, "nom": ligne, "cote": None, "musique": "Inconnu"}
        elif re.search(r'\d+[apmsh]', ligne.lower()) and current:
            current["musique"] = ligne
        else:
            cote_match = re.search(r'(\d+[\.,]\d+)', ligne)
            if cote_match and current and current["cote"] is None:
                current["cote"] = float(cote_match.group(1).replace(',', '.'))
    if current: partants.append(current)
    for p in partants: p["cote"] = p["cote"] if p["cote"] and p["cote"] > 1 else 20.0
    return pd.DataFrame(partants)

def expertise_web_pro(discipline, hippo, df):
    prompt = f"Analyse web pour {discipline} à {hippo}. Partants: {df.to_string()}"
    
    for tentative in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearchRetrieval())])
            )
            return response.text, None
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str:
                st.warning(f"⏳ Quota atteint. Tentative {tentative+1}/3... Pause de sécurité.")
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.05) # Pause de 5 secondes totale
                    progress_bar.progress(i + 1)
                continue
            return None, str(e)
    return None, "Quota Google saturé. Réessayez dans 1 minute."

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Intelligence Stratégique")

tab1, tab2 = st.tabs(["🚀 Analyse", "📊 Historique"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        discipline = st.selectbox("🎯 Discipline", ["Trot", "Galop", "Obstacle"])
        capital = st.number_input("💰 Capital (€)", value=500)
    with c2:
        hippo = st.text_input("📍 Hippodrome", value="Vincennes")
        txt_in = st.text_area("📋 Collez les partants ici :")

    if st.button("🚀 LANCER L'ANALYSE"):
        df_course = extraire_partants(txt_in)
        if not df_course.empty:
            with st.spinner("🌐 Recherche des dernières infos web..."):
                expertise, erreur = expertise_web_pro(discipline, hippo, df_course[['num', 'nom']])
            
            if expertise:
                st.markdown(f'<div class="gemini-box"><b>🧠 EXPERTISE LIVE :</b><br><br>{expertise}</div>', unsafe_allow_html=True)
            else:
                st.error(f"Mode Statistique (Web HS) : {erreur}")

            # Calculs
            resultats = []
            for _, row in df_course.iterrows():
                cote = max(row['cote'], 1.01)
                prob = (1 / cote) * 1.15
                podium = min(98, int((prob ** 0.7) * 220))
                f_kelly = (prob * (cote-1) - (1-prob)) / (cote-1)
                mise = min(max(0, capital * f_kelly * 0.15), capital * 0.10)
                resultats.append({**row, "cote": cote, "podium": podium, "mise": mise, "value": (prob*cote)-1})

            # Pari Maître
            p_maitre = max(resultats, key=lambda x: x['value'])
            if p_maitre['value'] > 0.05 and p_maitre['podium'] > 35:
                st.markdown(f"""
                <div class="master-bet">
                    <h3>🏆 PARI MAÎTRE CONSEILLÉ</h3>
                    <div style="font-size: 24px;"><b>n°{p_maitre['num']} - {p_maitre['nom']}</b></div>
                    <div>Cote : {p_maitre['cote']} | Confiance : {p_maitre['podium']}%</div>
                    <div style="font-size: 30px; margin-top:10px;">Mise : <b>{round(p_maitre['mise'], 2)}€</b></div>
                </div>
                """, unsafe_allow_html=True)

            # Liste
            st.write("---")
            cols = st.columns(3)
            for i, r in enumerate(sorted(resultats, key=lambda x: x['podium'], reverse=True)):
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="card">
                        <span class="num-badge">{r['num']}</span><b>{r['nom']}</b><br>
                        🎯 Podium : {r['podium']}% | Mise : {round(r['mise'], 2)}€
                    </div>
                    """, unsafe_allow_html=True)
