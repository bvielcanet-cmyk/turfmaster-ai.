import streamlit as st
import pandas as pd
import re
from datetime import datetime
import pytz

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI v8.6 Premium", page_icon="💎", layout="wide")
tz_paris = pytz.timezone('Europe/Paris')

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b0e14; color: #e2e8f0; }
    .stButton>button { background: linear-gradient(90deg, #059669 0%, #10b981 100%); border: none; color: white; font-weight: bold; border-radius: 10px; height: 3.5em; }
    .favori-glow { border: 2px solid #3b82f6; box-shadow: 0 0 15px rgba(59, 130, 246, 0.5); background: #172554; padding: 20px; border-radius: 15px; text-align: center; }
    .roi-card { background: #1a202c; padding: 10px; border-radius: 10px; border: 1px solid #2d3748; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

if 'bankroll' not in st.session_state: st.session_state.bankroll = 500.0
if 'total_mises' not in st.session_state: st.session_state.total_mises = 0.0
if 'total_gains' not in st.session_state: st.session_state.total_gains = 0.0

# --- LOGIQUE D'EXTRACTION V8.6 (INVERSÉE) ---
def extraire_donnees_v86(texte):
    partants = []
    # Normalisation
    texte = texte.replace(',', '.')
    
    # On cherche le pattern : Numéro (début ligne) -> Texte (Nom) -> Cote (décimale)
    # On utilise une regex qui capture le numéro, puis TOUT jusqu'à la cote
    pattern = re.compile(r"^\s*(\d{1,2})\b(.*?)\b(\d+\.\d+)\s*$", re.MULTILINE | re.DOTALL)
    
    # Alternative : Si le copier-coller est en un seul bloc compact
    if not pattern.search(texte):
        pattern = re.compile(r"(\d{1,2})\s+([A-ZÀ-Ÿ\s\-']{3,40}?)\s+.*?(\d+\.\d+)")

    # Découpage par ligne pour plus de précision sur les noms
    lignes = texte.split('\n')
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne: continue
        
        # On cherche : Nombre au début + Texte + Nombre décimal
        match = re.search(r"^(\d{1,2})\s+(.*?)\s+(\d+\.\d+)$", ligne)
        if match:
            num = match.group(1)
            nom = match.group(2).strip()
            cote = float(match.group(3))
            partants.append({"num": num, "nom": nom[:20], "cote": cote})
        else:
            # Si le nom et la cote sont sur des lignes différentes (format bloc)
            match_num = re.match(r"^(\d{1,2})$", ligne)
            if match_num:
                idx = lignes.index(ligne)
                num = match_num.group(1)
                nom = lignes[idx+1].strip() if idx+1 < len(lignes) else "INCONNU"
                # On cherche la cote dans les 4 lignes suivantes
                for j in range(2, 6):
                    if idx+j < len(lignes):
                        c_match = re.search(r"(\d+\.\d+)", lignes[idx+j])
                        if c_match:
                            partants.append({"num": num, "nom": nom[:20], "cote": float(c_match.group(1))})
                            break
            
    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- INTERFACE ---
st.title("🏇 TurfMaster AI v8.6 Premium")

with st.sidebar:
    st.header("📊 Performance")
    st.session_state.bankroll = st.number_input("Capital (€)", value=st.session_state.bankroll)
    roi = (((st.session_state.total_gains - st.session_state.total_mises) / st.session_state.total_mises) * 100) if st.session_state.total_mises > 0 else 0.0
    st.markdown(f'<div class="roi-card"><p>ROI GLOBAL</p><h2>{roi:.1f}%</h2></div>', unsafe_allow_html=True)
    if st.button("🔄 Reset"):
        st.session_state.total_mises = 0.0; st.session_state.total_gains = 0.0; st.rerun()

col_input, col_res = st.columns([1, 2])

with col_input:
    st.subheader("📥 Saisie")
    raw_data = st.text_area("Colle Zeturf ici", height=300, key="input_v86")
    if st.button("🚀 ANALYSER"):
        if raw_data:
            df = extraire_donnees_v86(raw_data)
            if not df.empty:
                st.session_state.last_df = df
            else: st.error("Format non reconnu.")

if 'last_df' in st.session_state:
    df = st.session_state.last_df
    with col_res:
        res_list = []
        for _, r in df.iterrows():
            p_estim = (1 / r['cote']) * 1.17
            v = p_estim * r['cote']
            fraction = 0.15 if r['cote'] < 6 else 0.08
            m = max(0, st.session_state.bankroll * ((p_estim * (r['cote']-1) - (1-p_estim)) / (r['cote']-1)) * fraction)
            res_list.append({"num": r['num'], "nom": r['nom'], "cote": r['cote'], "v": v, "m": m, "prob": p_estim})

        ordre = sorted(res_list, key=lambda x: x['prob'], reverse=True)
        top = ordre[0]
        
        # --- AFFICHAGE ---
        st.markdown(f'<div class="favori-glow"><h1 style="color:#fbbf24;">#{top["num"]} {top["nom"]}</h1><p>Cote : {top["cote"]} | IA : {top["prob"]*100:.1f}%</p></div>', unsafe_allow_html=True)

        st.subheader("💰 Mises Simple Gagnant")
        vals = [v for v in res_list if v['v'] > 1.05 and v['cote'] >= 1.5]
        if vals:
            for v in sorted(vals, key=lambda x: x['v'], reverse=True):
                st.success(f"**#{v['num']} {v['nom']}** → **{v['m']:.2f}€** (Cote: {v['cote']})")
        else: st.warning("Aucune Value.")

        st.subheader("🏆 Podium Estimé")
        for i, r in enumerate(ordre[:5]):
            st.write(f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'{i+1}è'} **#{r['num']} {r['nom']}** (Cote: {r['cote']})")

        with st.form("res_form"):
            m_f = st.number_input("Mise totale (€)", value=sum([v['m'] for v in vals]))
            g_o = st.number_input("Gain reçu (€)", value=0.0)
            if st.form_submit_button("Sauvegarder"):
                st.session_state.total_mises += m_f
                st.session_state.total_gains += g_o
                st.session_state.bankroll += (g_o - m_f)
                st.rerun()
