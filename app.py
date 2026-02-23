import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import re
import math

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Cloud", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

# Connexion Google Sheets Simplifiée (Mode Public)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # On force la lecture sans cache pour voir les mises à jour
        return conn.read(ttl=0)
    except Exception as e:
        # En cas d'erreur de lecture, on retourne un tableau vide
        return pd.DataFrame(columns=['date', 'discipline', 'hippodrome', 'num', 'resultat', 'avantage_ia'])

# Style CSS Pro (Lisibilité maximale en noir)
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .card { background-color: white; border-radius: 15px; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .num-badge { background-color: #34495e; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 10px; }
    .text-black { color: #000000 !important; font-weight: bold; }
    .text-black-small { color: #000000 !important; font-size: 14px; font-weight: 500; }
    .ia-status { background: #f0f2f6; padding: 10px; border-radius: 10px; font-size: 12px; border-left: 5px solid #28a745; margin-bottom: 15px; color: #000; }
    .pronostic-box { background-color: #ebf5fb; border-left: 5px solid #2980b9; padding: 10px; border-radius: 8px; margin-bottom: 20px; color: #000; }
    .value-text { color: #28a745; font-weight: bold; font-size: 16px; }
    .bet-advice { background-color: #fff4e6; color: #d9480f; padding: 4px 10px; border-radius: 5px; font-weight: bold; font-size: 13px; display: inline-block; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE EXPERTE ---

def conseiller_pari(cote, podium):
    if podium >= 85 and cote < 3: return "🎯 SIMPLE GAGNANT"
    elif podium >= 70 and cote >= 4: return "💰 SIMPLE PLACÉ"
    elif podium >= 65 and cote >= 10: return "💎 CHAQUE SENS (G/P)"
    elif podium >= 60: return "🔗 BASE COMBINAISON"
    else: return "🔭 COMPLÉMENT (Quinté)"

def analyser_musique(musique):
    if not musique or musique == "Inconnue": return 1.0
    score = 1.0
    resultats = re.findall(r'(\d|D|A|T)', musique)[:4]
    for i, res in enumerate(resultats):
        poids = 1 / (i + 1)
        if res == '1': score += 0.05 * poids
        elif res in ['2', '3']: score += 0.03 * poids
        elif res in ['D', 'A', 'T']: score -= 0.04 * poids
    return score

def obtenir_avantage_appris(df, discipline):
    if df is None or df.empty: return 1.12
    try:
        filtre = df[df['discipline'] == discipline].tail(20)
        if len(filtre) < 5: return 1.12
        reussite = pd.to_numeric(filtre['resultat']).mean()
        return 1.16 if reussite > 0.40 else 1.08 if reussite < 0.15 else 1.12
    except: return 1.12

# --- 3. EXTRACTION ---

def extraire_texte_intelligent(texte):
    blocs = re.split(r'\n(?=\d+\s*\n)', texte.strip())
    partants = []
    for bloc in blocs:
        lignes = [l.strip() for l in bloc.split('\n') if l.strip()]
        if len(lignes) >= 2:
            try:
                num, nom = lignes[0], lignes[1].upper()
                musique = next((l for l in lignes if re.search(r'\d+[apmsh]', l.lower())), "Inconnue")
                cote_matches = re.findall(r'(\d+[\.,]\d+)', bloc)
                if cote_matches:
                    cote = float(cote_matches[-1].replace(',', '.'))
                    partants.append({"num": num, "nom": nom, "cote": cote, "musique": musique})
            except: continue
    return pd.DataFrame(partants)

# --- 4. INTERFACE ---

st.title("🏇 TurfMaster AI Cloud (Public Sheet)")
df_ia = load_data()

tab1, tab2 = st.tabs(["🚀 Analyse Course", "📊 Mémoire Cloud"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        capital = st.number_input("💰 Mon Capital (€)", value=500)
        discipline = st.selectbox("🎯 Discipline", ["Trot 🐎", "Galop/Plat 🏇", "Obstacle/Haies 🪵"])
    with col2:
        hippo_manuel = st.text_input("📍 Hippodrome", value="Paris-Vincennes")

    adv_dynamique = obtenir_avantage_appris(df_ia, discipline)
    st.markdown(f"""<div class="ia-status">🤖 <b>Avantage Dynamique :</b> {adv_dynamique}</div>""", unsafe_allow_html=True)

    txt_in = st.text_area("1. Collez les partants :", height=150)
    if st.button("🚀 ANALYSER"):
        st.session_state.df_course = extraire_texte_intelligent(txt_in)

    if 'df_course' in st.session_state and not st.session_state.df_course.empty:
        resultats = []
        for _, row in st.session_state.df_course.iterrows():
            boost_m = analyser_musique(row['musique'])
            correction_v = 1 - (math.log(row['cote']) / 50) 
            prob_ia = (1 / row['cote']) * adv_dynamique * boost_m * correction_v
            
            val = prob_ia * row['cote']
            podium = min(98, int((prob_ia ** 0.7) * 100 * 2.2))
            f_kelly = (prob_ia * (row['cote'] - 1) - (1 - prob_ia)) / (row['cote'] - 1)
            mise = min(max(0, capital * f_kelly * 0.20), capital * 0.05)
            
            resultats.append({**row, "podium": podium, "mise": mise, "conseil": conseiller_pari(row['cote'], podium)})

        resultats = sorted(resultats, key=lambda x: x['podium'], reverse=True)
        st.session_state.derniers_resultats = resultats
        
        st.markdown(f"""<div class="pronostic-box"><b>🏁 ORDRE D'ARRIVÉE ESTIMÉ :</b><br>
        <span style="font-size: 20px;">{" - ".join([f"**{r['num']}**" for r in resultats[:5]])}</span></div>""", unsafe_allow_html=True)

        for i, res in enumerate(resultats):
            if res['podium'] >= 60 or i < 5:
                card_alpha = 1.0 if res['podium'] >= 60 else 0.75
                st.markdown(f"""
                <div class="card" style="opacity: {card_alpha};">
                    <span class="num-badge">{res['num']}</span><span class="text-black" style="font-size:18px;">{res['nom']}</span><br>
                    <span class="text-black-small">🎵 {res['musique']} | Cote : {res['cote']}</span><br>
                    <span class="text-black" style="font-size:16px;">Confiance Podium : {res['podium']}%</span><br>
                    <span class="value-text">Mise : {round(res['mise'], 2)}€</span><br>
                    <div class="bet-advice">💡 {res['conseil']}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("🏁 Enregistrer le résultat officiel")
        arrivee_txt = st.text_input("Collez l'arrivée (ex: 4-8-1) :")
        if st.button("💾 ENREGISTRER SUR GOOGLE SHEETS"):
            if arrivee_txt and 'derniers_resultats' in st.session_state:
                nums_gagnants = re.findall(r'\b(\d{1,2})\b', arrivee_txt)[:3]
                nouvelles_lignes = []
                for r in st.session_state.derniers_resultats:
                    est_p = 1 if str(r['num']) in nums_gagnants else 0
                    nouvelles_lignes.append({
                        'date': datetime.now(tz_paris).strftime("%Y-%m-%d %H:%M"),
                        'discipline': discipline, 'hippodrome': hippo_manuel,
                        'num': r['num'], 'resultat': est_p, 'avantage_ia': adv_dynamique
                    })
                df_maj = pd.concat([df_ia, pd.DataFrame(nouvelles_lignes)], ignore_index=True)
                # Tentative de mise à jour en mode public
                conn.update(data=df_maj)
                st.success("✅ Données sauvegardées avec succès !")
                st.rerun()

with tab2:
    st.header("📊 Historique & Mémoire")
    if df_ia is not None and not df_ia.empty:
        if st.checkbox("🔍 Voir les données brutes"):
            st.dataframe(df_ia.sort_index(ascending=False))
        
        st.subheader("Performance par discipline")
        stats = df_ia.groupby('discipline')['resultat'].agg(['mean', 'count']).reset_index()
        stats.columns = ['Discipline', '% Réussite', 'Nb Chevaux']
        stats['% Réussite'] = (pd.to_numeric(stats['mean']) * 100).round(1).astype(str) + "%"
        st.table(stats[['Discipline', '% Réussite', 'Nb Chevaux']])
    else:
        st.info("Le Google Sheet est vide ou n'est pas encore synchronisé.")
