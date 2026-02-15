import streamlit as st
import pandas as pd
import re
import requests
from datetime import datetime
import pytz

# --- CONFIGURATION PRO ---
st.set_page_config(page_title="TurfMaster AI v8.4 Premium", page_icon="💎", layout="wide")
tz_paris = pytz.timezone('Europe/Paris')

# Style Custom Premium Dark
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b0e14; color: #e2e8f0; }
    .stButton>button { background: linear-gradient(90deg, #059669 0%, #10b981 100%); border: none; color: white; font-weight: bold; border-radius: 10px; height: 3.5em; }
    .btn-reset>div>button { background: #334155 !important; }
    .favori-glow { border: 2px solid #3b82f6; box-shadow: 0 0 15px rgba(59, 130, 246, 0.5); background: #172554; padding: 20px; border-radius: 15px; text-align: center; }
    .roi-card { background: #1a202c; padding: 10px; border-radius: 10px; border: 1px solid #2d3748; text-align: center; }
    .num-badge { background-color: #fbbf24; color: #000; padding: 2px 8px; border-radius: 5px; font-weight: bold; margin-right: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION ---
if 'bankroll' not in st.session_state: st.session_state.bankroll = 500.0
if 'total_mises' not in st.session_state: st.session_state.total_mises = 0.0
if 'total_gains' not in st.session_state: st.session_state.total_gains = 0.0

# --- LOGIQUE D'EXTRACTION ULTRA-ROBUSTE ---
def extraire_donnees_v84(texte):
    partants = []
    texte = texte.replace(',', '.')
    # Regex : Numéro -> Saute à la ligne -> Nom Complet -> Saute lignes -> Cote décimale
    pattern = re.compile(r"(\b\d{1,2}\b)\s+([A-ZÀ-Ÿ0-9\s\-']{2,60}?).*?(\d+\.\d+)", re.DOTALL)
    
    for m in pattern.finditer(texte):
        num = m.group(1).strip()
        nom_brut = m.group(2).strip()
        
        # On prend la première ligne du nom et on enlève les espaces inutiles
        nom_final = nom_brut.split('\n')[0].strip()
        # On s'assure que le nom ne contient pas de débris (max 25 char)
        nom_final = re.sub(r'\s+', ' ', nom_final)[:25]

        try:
            cote = float(m.group(3))
            if cote > 1.0:
                partants.append({"num": num, "nom": nom_final, "cote": cote})
        except: continue
            
    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- INTERFACE ---
st.title("🏇 TurfMaster AI v8.4 Premium")

with st.sidebar:
    st.header("📊 Performance")
    st.session_state.bankroll = st.number_input("Capital Actuel (€)", value=st.session_state.bankroll)
    roi = (((st.session_state.total_gains - st.session_state.total_mises) / st.session_state.total_mises) * 100) if st.session_state.total_mises > 0 else 0.0
    st.markdown(f'<div class="roi-card"><p style="font-size:12px;">ROI GLOBAL</p><h2 style="color:{"#22c55e" if roi>=0 else "#ef4444"};">{roi:.1f}%</h2></div>', unsafe_allow_html=True)
    if st.button("🔄 Reset Statistiques"):
        st.session_state.total_mises = 0.0; st.session_state.total_gains = 0.0; st.rerun()

col_input, col_res = st.columns([1, 2])

with col_input:
    st.subheader("📥 Saisie Express")
    raw_data = st.text_area("Colle Zeturf ici", height=250, key="input_v84")
    c1, c2 = st.columns(2)
    with c1: btn_run = st.button("🚀 ANALYSER")
    with c2:
        if st.button("🗑️ VIDER"):
            st.session_state["input_v84"] = ""; st.rerun()
    st.markdown("[🔗 Ouvrir Zeturf](https://www.zeturf.fr/fr/paris-hippiques)")

if btn_run and raw_data:
    df = extraire_donnees_v84(raw_data)
    if not df.empty:
        with col_res:
            res_list = []
            for _, r in df.iterrows():
                p_estim = (1 / r['cote']) * 1.17 
                v = p_estim * r['cote']
                fraction = 0.15 if r['cote'] < 6 else 0.08
                m = max(0, st.session_state.bankroll * ((p_estim * (r['cote']-1) - (1-p_estim)) / (r['cote']-1)) * fraction)
                m = min(m, st.session_state.bankroll * 0.10) 
                res_list.append({"num": r['num'], "nom": r['nom'], "cote": r['cote'], "v": v, "m": m, "prob": p_estim})

            ordre = sorted(res_list, key=lambda x: x['prob'], reverse=True)
            top = ordre[0]
            values = [v for v in res_list if v['v'] > 1.05 and v['cote'] >= 1.5]
            
            # 1. FAVORI IA
            st.markdown(f'<div class="favori-glow"><h1 style="color:#fbbf24; margin:0;">#{top["num"]} {top["nom"]}</h1><p style="margin:0;">Cote : {top["cote"]} | IA : {top["prob"]*100:.1f}%</p></div>', unsafe_allow_html=True)

            # 2. MISES CONSEILLÉES
            st.subheader("💰 Mises Simple Gagnant")
            if values:
                for v in sorted(values, key=lambda x: x['v'], reverse=True):
                    st.success(f"**#{v['num']} {v['nom']}** → Miser : **{v['m']:.2f}€** (Cote: {v['cote']})")
            else: st.warning("Aucune Value détectée.")

            # 3. ESTIMATION ORDRE D'ARRIVÉE
            st.divider()
            st.subheader("🏆 Arrivée estimée (Podium)")
            for i, r in enumerate(ordre[:5]):
                medaille = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}è"
                st.write(f"{medaille} **#{r['num']} {r['nom']}** (Cote: {r['cote']})")

            # 4. TICKET RAPIDE
            st.subheader("🎫 Ticket à copier")
            st.code(" - ".join([r['num'] for r in ordre[:5]]))

            # 5. FORMULAIRE DE GAIN
            with st.form("result_v84"):
                mise_faite = st.number_input("Mise totale (€)", value=sum([v['m'] for v in values]))
                gain_obtenu = st.number_input("Gain reçu (€)", value=0.0)
                if st.form_submit_button("Calculer ROI & Sauvegarder"):
                    st.session_state.total_mises += mise_faite
                    st.session_state.total_gains += gain_obtenu
                    st.session_state.bankroll += (gain_obtenu - mise_faite)
                    st.rerun()
    else:
        st.error("Données non reconnues. Copie bien tout le bloc Zeturf.")

st.divider()
st.caption("TurfMaster AI v8.4 - Correction des noms & Réintégration du podium")
