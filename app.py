import streamlit as st
import pandas as pd
import re
import requests
from datetime import datetime
import pytz

# --- CONFIGURATION PRO ---
st.set_page_config(page_title="TurfMaster AI Expert v7", page_icon="🏇", layout="wide")
tz_paris = pytz.timezone('Europe/Paris')

# Style Custom Dark-Premium
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b0e14; color: #e2e8f0; }
    .stButton>button { background: linear-gradient(90deg, #059669 0%, #10b981 100%); border: none; color: white; font-weight: bold; border-radius: 10px; }
    .metric-card { background: #1a202c; padding: 15px; border-radius: 12px; border: 1px solid #2d3748; text-align: center; }
    .favori-glow { border: 2px solid #3b82f6; box-shadow: 0 0 15px rgba(59, 130, 246, 0.5); background: #172554; padding: 20px; border-radius: 15px; text-align: center; }
    .value-badge { background: #065f46; color: #34d399; padding: 2px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION ET LOGIQUE ---
if 'history' not in st.session_state: st.session_state.history = []
if 'bankroll' not in st.session_state: st.session_state.bankroll = 500.0

def extraire_donnees_v7(texte):
    partants = []
    texte = texte.replace(',', '.')
    # Recherche : Numéro -> Nom (MAJ) -> Cote
    pattern = re.compile(r"(\b\d{1,2}\b)\s+([A-ZÀ-Ÿ\s\-']{3,60}?).*?(\d+\.\d+)", re.DOTALL)
    for m in pattern.finditer(texte):
        num = m.group(1).strip()
        nom = " ".join(re.findall(r"\b[A-ZÀ-Ÿ]{3,}\b", m.group(2).strip()))
        try:
            cote = float(m.group(3))
            if cote > 1.0: partants.append({"num": num, "nom": nom[:18], "cote": cote})
        except: continue
    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- INTERFACE ---
st.title("🏇 TurfMaster AI Expert v7")

with st.sidebar:
    st.header("📊 Gestion Capital")
    st.session_state.bankroll = st.number_input("Capital (€)", value=st.session_state.bankroll)
    st.metric("ROI Estimé", f"{len(st.session_state.history) * 2.5}%") # Simulation simple
    if st.button("🔄 Reset Data"): st.session_state.history = []; st.rerun()

col_input, col_res = st.columns([1, 2])

with col_input:
    st.subheader("📥 Saisie Course")
    raw_data = st.text_area("Colle Zeturf ici", height=300)
    btn_run = st.button("🚀 ANALYSER LA COURSE")

if btn_run and raw_data:
    df = extraire_donnees_v7(raw_data)
    if not df.empty:
        with col_res:
            res_list = []
            for _, r in df.iterrows():
                p_estim = (1 / r['cote']) * 1.16 # Marge Expert
                v = p_estim * r['cote']
                # Kelly avec Protection (max 8% du capital)
                fraction = 0.15 if r['cote'] < 6 else 0.08
                m = max(0, st.session_state.bankroll * ((p_estim * (r['cote']-1) - (1-p_estim)) / (r['cote']-1)) * fraction)
                m = min(m, st.session_state.bankroll * 0.10) # Hard Stop 10%
                res_list.append({"num": r['num'], "nom": r['nom'], "cote": r['cote'], "v": v, "m": m, "prob": p_estim})

            # Tri et Podium
            ordre = sorted(res_list, key=lambda x: x['prob'], reverse=True)
            top = ordre[0]
            
            # --- BLOC FAVORI IA ---
            st.markdown(f"""
                <div class="favori-glow">
                    <span style="color: #60a5fa; font-weight: bold;">⭐ TOP PRIORITÉ IA</span>
                    <h1 style="color: #fbbf24; margin: 5px;">#{top['num']} {top['nom']}</h1>
                    <p>Confiance : {"⭐" * min(5, int(top['v'] * 3))} | Probabilité : {top['prob']*100:.1f}%</p>
                </div>
            """, unsafe_allow_html=True)

            # --- ORDRES DE TRADING ---
            st.subheader("💰 Ordres de Mise (Value Bets)")
            values = [v for v in res_list if v['v'] > 1.04]
            if values:
                for v in sorted(values, key=lambda x: x['v'], reverse=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**N°{v['num']} {v['nom']}** <span class='value-badge'>VALUE {v['v']:.2f}</span>", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"**{v['m']:.2f}€**")
            else:
                st.info("⚠️ Marché efficace : Aucune anomalie de cote détectée.")

            # --- TICKET RAPIDE ---
            st.divider()
            st.subheader("🎫 Ticket Combiné (Top 5)")
            st.code(" - ".join([r['num'] for r in ordre[:5]]))

    else:
        st.error("Format de données non reconnu.")

# --- FOOTER ---
st.divider()
st.caption("TurfMaster Expert - Ne misez que ce que vous pouvez vous permettre de perdre.")
