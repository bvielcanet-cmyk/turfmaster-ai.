import streamlit as st
import pandas as pd
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI v10 Market-Watch", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b1120; color: #f8fafc; }
    .stButton>button { background: linear-gradient(90deg, #10b981 0%, #059669 100%); border: none; color: white; font-weight: bold; border-radius: 12px; height: 3.5em; }
    .market-up { color: #10b981; font-weight: bold; font-size: 0.9em; }
    .market-down { color: #ef4444; font-weight: bold; font-size: 0.9em; }
    .favori-glow { border: 2px solid #3b82f6; background: #1e293b; padding: 20px; border-radius: 20px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# Initialisation
if 'bankroll' not in st.session_state: st.session_state.bankroll = 500.0
if 'total_mises' not in st.session_state: st.session_state.total_mises = 0.0
if 'total_gains' not in st.session_state: st.session_state.total_gains = 0.0
if 'last_cotes' not in st.session_state: st.session_state.last_cotes = {}

def extraire_donnees_v10(texte):
    partants = []
    texte = texte.replace(',', '.')
    lignes = [l.strip() for l in texte.split('\n') if l.strip()]
    for i in range(len(lignes)):
        ligne = lignes[i]
        match_ligne = re.search(r"^(\d{1,2})\s+(.*?)\s+(\d+\.\d+)$", ligne)
        if match_ligne:
            partants.append({"num": match_ligne.group(1), "nom": match_ligne.group(2).strip(), "cote": float(match_ligne.group(3))})
        elif re.match(r"^(\d{1,2})$", ligne):
            num = ligne
            nom = lignes[i+1].strip() if i+1 < len(lignes) else "INCONNU"
            cote = next((float(re.search(r"(\d+\.\d+)", lignes[i+j]).group(1)) for j in range(1, 6) if i+j < len(lignes) and re.search(r"(\d+\.\d+)", lignes[i+j])), None)
            if cote: partants.append({"num": num, "nom": nom, "cote": cote})
    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- INTERFACE ---
st.title("🏇 TurfMaster AI v10 Market-Watch")

with st.sidebar:
    st.header("📈 Bankroll")
    st.session_state.bankroll = st.number_input("Capital (€)", value=st.session_state.bankroll)
    roi = (((st.session_state.total_gains - st.session_state.total_mises) / st.session_state.total_mises) * 100) if st.session_state.total_mises > 0 else 0.0
    st.metric("ROI GLOBAL", f"{roi:.1f}%", delta=f"{st.session_state.total_gains - st.session_state.total_mises:.2f}€")

col_input, col_res = st.columns([1, 2])

with col_input:
    st.subheader("📥 Saisie Course")
    raw_data = st.text_area("Colle Zeturf ici", height=300, key="input_v10")
    if st.button("🚀 ANALYSER & COMPARER"):
        df = extraire_donnees_v10(raw_data)
        if not df.empty:
            st.session_state.current_df = df
        else: st.error("Format non reconnu.")

if 'current_df' in st.session_state:
    df = st.session_state.current_df
    with col_res:
        res_list = []
        for _, r in df.iterrows():
            # Détection mouvement de cote
            anc_cote = st.session_state.last_cotes.get(r['num'], r['cote'])
            mouvement = ""
            if r['cote'] < anc_cote: mouvement = f"🔥 Baisse (-{((anc_cote-r['cote'])/anc_cote)*100:.1f}%)"
            elif r['cote'] > anc_cote: mouvement = f"🧊 Hausse (+{((r['cote']-anc_cote)/anc_cote)*100:.1f}%)"
            
            # Algorithme Neural-Engine v10
            p_pure = 1 / r['cote']
            # Bonus si la cote baisse (argent intelligent détecté)
            bonus_market = 1.05 if r['cote'] < anc_cote else 1.0
            marge = (1.12 if r['cote'] < 4 else 1.20 if r['cote'] < 12 else 1.30) * bonus_market
            p_estim = p_pure * marge
            
            v = p_estim * r['cote']
            m = max(0, st.session_state.bankroll * ((p_estim * (r['cote']-1) - (1-p_estim)) / (r['cote']-1)) * 0.08)
            
            res_list.append({"num": r['num'], "nom": r['nom'], "cote": r['cote'], "v": v, "m": m, "prob": p_estim, "mouv": mouvement})

        # Mise à jour de la mémoire pour le prochain scan
        st.session_state.last_cotes = {r['num']: r['cote'] for r in res_list}

        ordre = sorted(res_list, key=lambda x: x['prob'], reverse=True)
        top = ordre[0]
        
        st.markdown(f'<div class="favori-glow"><h1 style="color:#fbbf24;">#{top["num"]} {top["nom"]}</h1><p>Cote: {top["cote"]} | Probabilité: {top["prob"]*100:.1f}%</p></div>', unsafe_allow_html=True)

        st.subheader("💰 Opportunités de Mise")
        for v in sorted(res_list, key=lambda x: x['v'], reverse=True):
            if v['v'] > 1.08:
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.write(f"**#{v['num']} {v['nom']}** | Value: {v['v']:.2f} | <span class='market-up'>{v['mouv']}</span>", unsafe_allow_html=True)
                with col_b:
                    st.write(f"**{v['m']:.2f}€**")

        st.divider()
        st.subheader("📝 Enregistrer résultat")
        with st.form("roi_v10"):
            m_f = st.number_input("Mise totale", value=sum([v['m'] for v in res_list if v['v'] > 1.08]))
            g_o = st.number_input("Gain reçu", value=0.0)
            if st.form_submit_button("VALIDER"):
                st.session_state.total_mises += m_f
                st.session_state.total_gains += g_o
                st.session_state.bankroll += (g_o - m_f)
                st.rerun()
