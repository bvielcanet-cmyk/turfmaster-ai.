import streamlit as st
import pandas as pd
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI v8.8 Premium", page_icon="💎", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b0e14; color: #e2e8f0; }
    .stButton>button { background: linear-gradient(90deg, #059669 0%, #10b981 100%); border: none; color: white; font-weight: bold; border-radius: 10px; height: 3.5em; }
    .favori-glow { border: 2px solid #3b82f6; box-shadow: 0 0 15px rgba(59, 130, 246, 0.5); background: #172554; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .roi-card { background: #1a202c; padding: 10px; border-radius: 10px; border: 1px solid #2d3748; text-align: center; }
    .conseil-box { background: #1e293b; border-left: 5px solid #fbbf24; padding: 15px; border-radius: 8px; margin-top: 15px; color: #f1f5f9; font-size: 1.1em; }
    </style>
    """, unsafe_allow_html=True)

if 'bankroll' not in st.session_state: st.session_state.bankroll = 500.0
if 'total_mises' not in st.session_state: st.session_state.total_mises = 0.0
if 'total_gains' not in st.session_state: st.session_state.total_gains = 0.0

# --- LOGIQUE D'EXTRACTION SÉCURISÉE ---
def extraire_donnees_v88(texte):
    partants = []
    texte = texte.replace(',', '.')
    lignes = [l.strip() for l in texte.split('\n')]
    
    for i in range(len(lignes)):
        ligne = lignes[i]
        if not ligne: continue
        
        # CAS 1 : Ligne complète (Numéro Nom Cote)
        match_ligne = re.search(r"^(\d{1,2})\s+(.*?)\s+(\d+\.\d+)$", ligne)
        if match_ligne:
            partants.append({
                "num": match_ligne.group(1),
                "nom": match_ligne.group(2).strip(),
                "cote": float(match_ligne.group(3))
            })
            continue

        # CAS 2 : Format Bloc (Numéro seul)
        if re.match(r"^(\d{1,2})$", ligne):
            num = ligne
            nom = "INCONNU"
            cote = None
            if i + 1 < len(lignes):
                nom = lignes[i+1].strip()
            for j in range(1, 6):
                if i + j < len(lignes):
                    c_match = re.search(r"(\d+\.\d+)", lignes[i+j])
                    if c_match:
                        cote = float(c_match.group(1))
                        break
            if cote:
                partants.append({"num": num, "nom": nom, "cote": cote})
            
    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- INTERFACE ---
st.title("🏇 TurfMaster AI v8.8 Premium")

with st.sidebar:
    st.header("📊 Performance")
    st.session_state.bankroll = st.number_input("Capital (€)", value=st.session_state.bankroll)
    roi = (((st.session_state.total_gains - st.session_state.total_mises) / st.session_state.total_mises) * 100) if st.session_state.total_mises > 0 else 0.0
    st.markdown(f'<div class="roi-card"><p>ROI GLOBAL</p><h2>{roi:.1f}%</h2></div>', unsafe_allow_html=True)
    if st.button("🔄 Reset"):
        st.session_state.total_mises = 0.0; st.session_state.total_gains = 0.0; st.rerun()

col_input, col_res = st.columns([1, 2])

with col_input:
    st.subheader("📥 Saisie Express")
    raw_data = st.text_area("Colle Zeturf ici", height=300, key="input_v88")
    c1, c2 = st.columns(2)
    with c1: btn_run = st.button("🚀 ANALYSER")
    with c2:
        if st.button("🗑️ VIDER"):
            st.session_state["input_v88"] = ""; st.rerun()

if btn_run and raw_data:
    df = extraire_donnees_v88(raw_data)
    if not df.empty:
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
            vals = [v for v in res_list if v['v'] > 1.05 and v['cote'] >= 1.5]
            
            # 1. FAVORI IA
            st.markdown(f'<div class="favori-glow"><p style="margin:0;color:#60a5fa;">LE PLUS PROBABLE</p><h1 style="color:#fbbf24; margin:5px;">#{top["num"]} {top["nom"]}</h1><p style="margin:0;">Cote : {top["cote"]} | IA : {top["prob"]*100:.1f}%</p></div>', unsafe_allow_html=True)

            # 2. CONSEIL DE PARI
            st.subheader("💡 Conseil de Jeu")
            if not vals:
                conseil = "⚠️ **PAS DE VALUE** : Les cotes sont trop précises. Attendez la prochaine course."
            elif len(vals) == 1:
                conseil = f"🎯 **SIMPLE GAGNANT** : Tout sur le **#{vals[0]['num']}** ({vals[0]['m']:.2f}€)."
            else:
                top_vals = sorted(vals, key=lambda x: x['v'], reverse=True)
                conseil = f"🔥 **STRATÉGIE VALEUR** : Simple Gagnant sur le **#{top_vals[0]['num']}** et le **#{top_vals[1]['num']}**. Duo possible en **Couplé Gagnant**."
            st.markdown(f'<div class="conseil-box">{conseil}</div>', unsafe_allow_html=True)

            # 3. ORDRES DE MISE
            st.subheader("💰 Mises à placer")
            if vals:
                for v in sorted(vals, key=lambda x: x['v'], reverse=True):
                    st.success(f"**#{v['num']} {v['nom']}** → **{v['m']:.2f}€** (Cote: {v['cote']})")

            # 4. PODIUM ARRIVÉE ESTIMÉE
            st.divider()
            st.subheader("🏆 Arrivée estimée (Podium)")
            for i, r in enumerate(ordre[:5]):
                medaille = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}è"
                st.write(f"{medaille} **#{r['num']} {r['nom']}** (Cote: {r['cote']})")

            # 5. TICKET À COPIER
            st.subheader("🎫 Ticket à copier")
            st.code(" - ".join([r['num'] for r in ordre[:5]]))

            with st.form("res_form_v88"):
                m_f = st.number_input("Mise totale (€)", value=sum([v['m'] for v in vals]))
                g_o = st.number_input("Gain reçu (€)", value=0.0)
                if st.form_submit_button("Sauvegarder Résultat"):
                    st.session_state.total_mises += m_f
                    st.session_state.total_gains += g_o
                    st.session_state.bankroll += (g_o - m_f)
                    st.rerun()
    else:
        st.error("Format non reconnu.")
