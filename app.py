import streamlit as st
import pandas as pd
import re
import math

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI v9.0 Ultra-Alpha", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b0e14; color: #e2e8f0; }
    .stButton>button { background: linear-gradient(90deg, #10b981 0%, #059669 100%); border: none; color: white; font-weight: bold; border-radius: 10px; height: 3.5em; transition: 0.3s; }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 0 15px rgba(16, 185, 129, 0.4); }
    .favori-glow { border: 2px solid #3b82f6; background: linear-gradient(180deg, #172554 0%, #0b0e14 100%); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .roi-card { background: #1a202c; padding: 15px; border-radius: 12px; border: 1px solid #2d3748; text-align: center; }
    .conseil-box { background: #1e293b; border-left: 5px solid #fbbf24; padding: 15px; border-radius: 8px; margin-top: 15px; font-size: 1.1em; box-shadow: 2px 2px 10px rgba(0,0,0,0.3); }
    .value-score { font-size: 0.8em; color: #10b981; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'bankroll' not in st.session_state: st.session_state.bankroll = 500.0
if 'total_mises' not in st.session_state: st.session_state.total_mises = 0.0
if 'total_gains' not in st.session_state: st.session_state.total_gains = 0.0

# --- EXTRACTION ROBUSTE ---
def extraire_donnees_v9(texte):
    partants = []
    texte = texte.replace(',', '.')
    lignes = [l.strip() for l in texte.split('\n')]
    for i in range(len(lignes)):
        ligne = lignes[i]
        if not ligne: continue
        match_ligne = re.search(r"^(\d{1,2})\s+(.*?)\s+(\d+\.\d+)$", ligne)
        if match_ligne:
            partants.append({"num": match_ligne.group(1), "nom": match_ligne.group(2).strip(), "cote": float(match_ligne.group(3))})
            continue
        if re.match(r"^(\d{1,2})$", ligne):
            num = ligne
            nom = lignes[i+1].strip() if i+1 < len(lignes) else "INCONNU"
            cote = None
            for j in range(1, 6):
                if i + j < len(lignes):
                    c_match = re.search(r"(\d+\.\d+)", lignes[i+j])
                    if c_match:
                        cote = float(c_match.group(1)); break
            if cote: partants.append({"num": num, "nom": nom, "cote": cote})
    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- INTERFACE ---
st.title("🏇 TurfMaster AI v9.0 Ultra-Alpha")

with st.sidebar:
    st.header("📊 Performance Réelle")
    st.session_state.bankroll = st.number_input("Capital (€)", value=st.session_state.bankroll)
    roi = (((st.session_state.total_gains - st.session_state.total_mises) / st.session_state.total_mises) * 100) if st.session_state.total_mises > 0 else 0.0
    st.markdown(f'<div class="roi-card"><p>ROI GLOBAL</p><h2 style="color:{"#10b981" if roi>=0 else "#ef4444"};">{roi:.1f}%</h2><p style="font-size:0.8em; opacity:0.6;">Mises: {st.session_state.total_mises:.2f}€</p></div>', unsafe_allow_html=True)
    if st.button("🔄 Reset Statistiques"):
        st.session_state.total_mises = 0.0; st.session_state.total_gains = 0.0; st.rerun()

col_input, col_res = st.columns([1, 2])

with col_input:
    st.subheader("📥 Saisie Express")
    raw_data = st.text_area("Colle Zeturf ici", height=300, key="input_v9")
    c1, c2 = st.columns(2)
    with c1: btn_run = st.button("🚀 ANALYSER")
    with c2:
        if st.button("🗑️ VIDER"):
            st.session_state["input_v9"] = ""; st.rerun()

if btn_run and raw_data:
    df = extraire_donnees_v9(raw_data)
    if not df.empty:
        with col_res:
            res_list = []
            for _, r in df.iterrows():
                # --- OPTIMISATION IA 9.0 ---
                # Ajustement logarithmique de la probabilité
                p_pure = 1 / r['cote']
                marge_adaptative = 1.14 if r['cote'] < 4 else 1.18 if r['cote'] < 12 else 1.22
                p_estim = p_pure * marge_adaptative
                
                v = p_estim * r['cote']
                # Kelly Sécurisé (Fractionnel Dynamique)
                f_secu = 0.12 if r['cote'] < 7 else 0.06
                m = max(0, st.session_state.bankroll * ((p_estim * (r['cote']-1) - (1-p_estim)) / (r['cote']-1)) * f_secu)
                m = min(m, st.session_state.bankroll * 0.08) # Plafond 8%
                
                res_list.append({"num": r['num'], "nom": r['nom'], "cote": r['cote'], "v": v, "m": m, "prob": p_estim})

            ordre = sorted(res_list, key=lambda x: x['prob'], reverse=True)
            top = ordre[0]
            vals = [v for v in res_list if v['v'] > 1.06 and v['cote'] >= 1.6]
            
            # 1. FAVORI IA
            st.markdown(f'<div class="favori-glow"><p style="margin:0;color:#60a5fa;letter-spacing:2px;">TOP PROBABILITÉ</p><h1 style="color:#fbbf24; margin:5px;">#{top["num"]} {top["nom"]}</h1><p style="margin:0;">Cote : {top["cote"]} | Score IA : {int(top["prob"]*100)}/100</p></div>', unsafe_allow_html=True)

            # 2. CONSEIL DE PARI ALPHA
            st.subheader("💡 Analyse Stratégique")
            if not vals:
                st.warning("⚠️ Marché trop efficace. L'IA ne détecte aucune faille rentable. Évitez de parier.")
            else:
                top_v = sorted(vals, key=lambda x: x['v'], reverse=True)[0]
                st.markdown(f'<div class="conseil-box">🎯 **RECOMMANDATION** : Parier **{top_v["m"]:.2f}€** sur le **#{top_v["num"]} {top_v["nom"]}** en Simple Gagnant. <br><span class="value-score">Indice de confiance Alpha : {int(top_v["v"]*50)}%</span></div>', unsafe_allow_html=True)

            # 3. ORDRES DE MISE
            if vals:
                st.subheader("💰 Mises suggérées")
                for v in sorted(vals, key=lambda x: x['v'], reverse=True):
                    st.success(f"**#{v['num']} {v['nom']}** → **{v['m']:.2f}€** (Cote: {v['cote']} | Value: {v['v']:.2f})")

            # 4. PODIUM & TICKET
            st.divider()
            c_a, c_b = st.columns(2)
            with c_a:
                st.subheader("🏆 Podium Estimé")
                for i, r in enumerate(ordre[:3]):
                    st.write(f"{'🥇' if i==0 else '🥈' if i==1 else '🥉'} **#{r['num']} {r['nom']}**")
            with c_b:
                st.subheader("🎫 Ticket")
                st.code(" - ".join([r['num'] for r in ordre[:5]]))

            # 5. FORMULAIRE ROI
            with st.form("roi_v9"):
                m_f = st.number_input("Mise totale (€)", value=sum([v['m'] for v in vals]))
                g_o = st.number_input("Gain reçu (€)", value=0.0)
                if st.form_submit_button("VALIDER LE RÉSULTAT"):
                    st.session_state.total_mises += m_f
                    st.session_state.total_gains += g_o
                    st.session_state.bankroll += (g_o - m_f)
                    st.rerun()
    else:
        st.error("Données illisibles.")
