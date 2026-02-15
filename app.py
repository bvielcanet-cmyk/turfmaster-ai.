import streamlit as st
import pandas as pd
import re
import requests
from datetime import datetime
import pytz

# --- CONFIGURATION PRO ---
st.set_page_config(page_title="TurfMaster AI Expert v7.5", page_icon="🏇", layout="wide")
tz_paris = pytz.timezone('Europe/Paris')

# Style Custom Dark-Premium
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b0e14; color: #e2e8f0; }
    .stButton>button { background: linear-gradient(90deg, #059669 0%, #10b981 100%); border: none; color: white; font-weight: bold; border-radius: 10px; height: 3em; }
    .btn-reset>div>button { background: #334155 !important; }
    .metric-card { background: #1a202c; padding: 15px; border-radius: 12px; border: 1px solid #2d3748; text-align: center; }
    .favori-glow { border: 2px solid #3b82f6; box-shadow: 0 0 15px rgba(59, 130, 246, 0.5); background: #172554; padding: 20px; border-radius: 15px; text-align: center; }
    .value-badge { background: #065f46; color: #34d399; padding: 2px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .conseil-box { background: #1e293b; border-left: 5px solid #fbbf24; padding: 15px; border-radius: 8px; margin-top: 15px; color: #f1f5f9; }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION ET LOGIQUE ---
if 'bankroll' not in st.session_state: st.session_state.bankroll = 500.0

def extraire_donnees_v7(texte):
    partants = []
    texte = texte.replace(',', '.')
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
st.title("🏇 TurfMaster AI Expert v7.5")

with st.sidebar:
    st.header("📊 Gestion Capital")
    st.session_state.bankroll = st.number_input("Capital (€)", value=st.session_state.bankroll)
    st.divider()
    st.caption("Le conseil s'affiche après l'analyse.")

col_input, col_res = st.columns([1, 2])

with col_input:
    st.subheader("📥 Saisie Course")
    # Utilisation d'une clé pour le text_area pour permettre le reset
    raw_data = st.text_area("Colle Zeturf ici", height=300, key="input_data")
    
    c1, c2 = st.columns(2)
    with c1:
        btn_run = st.button("🚀 ANALYSER")
    with c2:
        # Bouton Reset : vide l'entrée en rechargeant l'app
        st.markdown('<div class="btn-reset">', unsafe_allow_html=True)
        if st.button("🗑️ VIDER"):
            st.session_state["input_data"] = ""
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

if btn_run and raw_data:
    df = extraire_donnees_v7(raw_data)
    if not df.empty:
        with col_res:
            res_list = []
            for _, r in df.iterrows():
                p_estim = (1 / r['cote']) * 1.16 
                v = p_estim * r['cote']
                fraction = 0.15 if r['cote'] < 6 else 0.08
                m = max(0, st.session_state.bankroll * ((p_estim * (r['cote']-1) - (1-p_estim)) / (row['cote']-1) if r['cote']>1 else 0) * fraction)
                # Correction calcul mise Kelly simplifié
                m = max(0, st.session_state.bankroll * ((p_estim - (1-p_estim)/(r['cote']-1)) if r['cote']>1 else 0) * fraction)
                m = min(m, st.session_state.bankroll * 0.10) 
                res_list.append({"num": r['num'], "nom": r['nom'], "cote": r['cote'], "v": v, "m": m, "prob": p_estim})

            ordre = sorted(res_list, key=lambda x: x['prob'], reverse=True)
            top = ordre[0]
            values = [v for v in res_list if v['v'] > 1.04]
            
            # --- BLOC FAVORI IA ---
            st.markdown(f"""
                <div class="favori-glow">
                    <span style="color: #60a5fa; font-weight: bold;">⭐ TOP PRIORITÉ IA</span>
                    <h1 style="color: #fbbf24; margin: 5px;">#{top['num']} {top['nom']}</h1>
                    <p>Cote : {top['cote']} | Probabilité : {top['prob']*100:.1f}%</p>
                </div>
            """, unsafe_allow_html=True)

            # --- CONSEIL DE PARI (DYNAMIQUE) ---
            st.subheader("💡 Conseil de Jeu")
            type_pari = ""
            if not values:
                type_pari = "⚠️ **PAS DE MISE CONSEILLÉE** : Le marché est trop précis. Ne forcez pas, attendez la prochaine course ou tentez un petit **Simple Placé** sur le #" + top['num'] + "."
            elif len(values) == 1:
                v = values[0]
                type_pari = f"🎯 **SIMPLE GAGNANT** : Misez **{v['m']:.2f}€** sur le **#{v['num']} {v['nom']}**. C'est le seul cheval avec un avantage mathématique réel."
            else:
                top_v = sorted(values, key=lambda x: x['v'], reverse=True)
                type_pari = f"🔥 **STRATÉGIE VALEUR** : Misez en Simple Gagnant sur le **#{top_v[0]['num']}** ({top_v[0]['m']:.2f}€) et le **#{top_v[1]['num']}** ({top_v[1]['m']:.2f}€). Pour un gros gain, tentez un **Couplé Gagnant** combiné entre ces deux chevaux."
            
            st.markdown(f'<div class="conseil-box">{type_pari}</div>', unsafe_allow_html=True)

            # --- ORDRES DE TRADING ---
            st.subheader("💰 Détails des Mises")
            if values:
                for v in sorted(values, key=lambda x: x['v'], reverse=True):
                    st.markdown(f"**#{v['num']} {v['nom']}** → Mise : **{v['m']:.2f}€** (Cote: {v['cote']} | Value: {v['v']:.2f})")
            
            st.divider()
            st.subheader("🎫 Ticket Top 5 (Combiné)")
            st.code(" - ".join([r['num'] for r in ordre[:5]]))

    else:
        st.error("Format de données non reconnu.")

st.divider()
st.caption("TurfMaster Expert v7.5 - Optimisé pour Zeturf Mobile")
