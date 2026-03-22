import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Expert Pronos", page_icon="🏇", layout="wide")

if "gemini" in st.secrets and "api_key" in st.secrets["gemini"]:
    client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("❌ Clé API Gemini manquante dans les Secrets.")
    st.stop()

# Styles CSS Pro
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; border: none; }
    .master-bet { 
        background: linear-gradient(135deg, #1e5b2e 0%, #28a745 100%); 
        color: white; padding: 25px; border-radius: 15px; border: 2px solid #ffd700; 
        box-shadow: 0px 10px 20px rgba(0,0,0,0.2); margin-bottom: 25px; text-align: center;
    }
    .arrival-box { background-color: #e3f2fd; border: 2px solid #2196f3; padding: 15px; border-radius: 10px; color: #0d47a1; text-align: center; margin-bottom: 20px; font-weight: bold; }
    .card { background-color: white; border-radius: 12px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; color: #000; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .num-badge { background-color: #34495e; color: white; padding: 2px 8px; border-radius: 5px; font-weight: bold; margin-right: 8px; }
    .gemini-box { background-color: #f3e5f5; border-left: 5px solid #9c27b0; padding: 15px; border-radius: 10px; color: #4a148c; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS MOTEUR ---

def extraire_partants_robuste(texte):
    partants = []
    texte = texte.replace('\xa0', ' ').replace('\t', ' ')
    lignes = texte.strip().split('\n')
    current_horse = None
    compteur_auto = 1
    
    for i, ligne in enumerate(lignes):
        ligne = ligne.strip()
        if not ligne: continue
        # Détection Nom (Majuscules)
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            if current_horse: partants.append(current_horse)
            num_f = str(compteur_auto)
            if i > 0 and lignes[i-1].strip().isdigit(): num_f = lignes[i-1].strip()
            current_horse = {"num": num_f, "nom": ligne, "cote": None, "musique": "Inconnue"}
            compteur_auto += 1
        # Musique
        elif re.search(r'\d+[apmsh]', ligne.lower()) and current_horse:
            current_horse["musique"] = ligne
        # Cote
        else:
            cote_match = re.search(r'(\d+[\.,]\d+)', ligne)
            if cote_match and current_horse and current_horse["cote"] is None:
                current_horse["cote"] = float(cote_match.group(1).replace(',', '.'))
            
    if current_horse: partants.append(current_horse)
    for p in partants:
        if p["cote"] is None or p["cote"] <= 1.0: p["cote"] = 20.0
    return pd.DataFrame(partants)

def analyse_gemini_hybride(discipline, hippo, df_partants):
    """Tente la recherche web, sinon bascule sur l'analyse de données pure."""
    partants_str = df_partants[['num', 'nom', 'cote', 'musique']].to_string()
    prompt = f"""Expert Turf : Analyse la course de {discipline} à {hippo}.
    Données : {partants_str}
    
    1. Analyse brièvement les chances des favoris selon leur musique.
    2. Identifie un outsider capable de casser le tiercé.
    3. PROPOSE UNE ARRIVÉE ESTIMÉE (Top 3) claire.
    """
    
    try:
        # Tentative avec recherche Web (Syntaxe stable)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearchRetrieval())],
                temperature=0.3
            )
        )
        return response.text, "✅ Analyse Web Live"
    except Exception:
        # Fallback : Analyse IA pure (sans outils bloquants)
        try:
            response_fallback = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"MODE STATISTIQUE : {prompt}",
                config=types.GenerateContentConfig(temperature=0.3)
            )
            return response_fallback.text, "🛡️ Analyse Statistique (Web Saturé)"
        except Exception as e:
            return None, f"Erreur API : {str(e)}"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Intelligence & Pronos")

c1, c2 = st.columns(2)
with c1:
    discipline = st.selectbox("🎯 Discipline", ["Trot", "Galop", "Obstacle"])
    capital = st.number_input("💰 Capital (€)", value=500)
with c2:
    hippo = st.text_input("📍 Hippodrome", value="Paris-Vincennes")
    txt_in = st.text_area("📋 Partants :", height=100, placeholder="JIJI DOUZOU\n26.6\nJUST IN DE BLARY\n...")

if st.button("🔍 ANALYSER LA COURSE"):
    df = extraire_partants_robuste(txt_in)
    
    if not df.empty:
        # 1. Analyse Gemini
        with st.spinner("🧠 Gemini analyse les données..."):
            expertise, source = analyse_gemini_hybride(discipline, hippo, df)
        
        if expertise:
            st.markdown(f'<div class="gemini-box"><b>{source} :</b><br><br>{expertise}</div>', unsafe_allow_html=True)
        
        # 2. Calculs Mathématiques
        resultats = []
        best_v = -1
        p_maitre = None
        
        for _, row in df.iterrows():
            c_safe = max(float(row['cote']), 1.01)
            prob_ia = (1 / c_safe) * 1.15
            podium = min(98, int((prob_ia ** 0.7) * 220))
            # Kelly
            f_k = (prob_ia * (c_safe-1) - (1-prob_ia)) / (c_safe-1)
            mise = min(max(0, capital * f_k * 0.15), capital * 0.10)
            val = (prob_ia * c_safe) - 1
            
            res_obj = {**row, "cote": c_safe, "podium": podium, "mise": mise, "value": val}
            resultats.append(res_obj)
            if val > best_v:
                best_v = val
                p_maitre = res_obj

        # 3. Affichage Arrivée Estimée (Top 3 Statistique)
        tri_podium = sorted(resultats, key=lambda x: x['podium'], reverse=True)
        arrivee_str = " - ".join([f"n°{x['num']}" for x in tri_podium[:3]])
        st.markdown(f'<div class="arrival-box">🏁 ARRIVÉE ESTIMÉE (STATS) : {arrivee_str}</div>', unsafe_allow_html=True)

        # 4. Pari Maître
        if p_maitre and best_v > 0.05 and p_maitre['podium'] > 35:
            st.markdown(f"""
            <div class="master-bet">
                <h3>🏆 PARI MAÎTRE : n°{p_maitre['num']} - {p_maitre['nom']}</h3>
                <div style="font-size: 32px;">Mise : <b>{round(p_maitre['mise'], 2)}€</b></div>
                <div>Cote : {p_maitre['cote']} | Confiance : {p_maitre['podium']}%</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("⚠️ Pas de pari maître détecté (Value trop faible).")

        # 5. Grille
        st.write("---")
        cols = st.columns(3)
        for i, r in enumerate(tri_podium):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="card">
                    <span class="num-badge">{r['num']}</span><b>{r['nom']}</b><br>
                    🎯 Podium : {r['podium']}% | Cote : {r['cote']}<br>
                    <span style="color: #28a745; font-weight:bold;">Mise : {round(r['mise'], 2)}€</span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.error("Aucun cheval détecté.")
