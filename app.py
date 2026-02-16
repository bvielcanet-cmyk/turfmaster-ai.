import streamlit as st
import pandas as pd
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI v11 - SplitView", page_icon="💎", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b1120; color: #f8fafc; }
    .stButton>button { background: linear-gradient(90deg, #10b981 0%, #059669 100%); border: none; color: white; font-weight: bold; border-radius: 12px; height: 3.5em; width: 100%; }
    .favori-glow { border: 2px solid #3b82f6; background: #1e293b; padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .roi-card { background: #1a202c; padding: 10px; border-radius: 10px; border: 1px solid #334155; text-align: center; }
    .podium-box { background: #0f172a; padding: 15px; border-radius: 10px; border: 1px solid #1e293b; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Initialisation
if 'bankroll' not in st.session_state: st.session_state.bankroll = 500.0
if 'total_mises' not in st.session_state: st.session_state.total_mises = 0.0
if 'total_gains' not in st.session_state: st.session_state.total_gains = 0.0

# --- EXTRACTION ---
def extraire_donnees_v11(texte):
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
st.title("🏇 TurfMaster AI v11 - SplitView")

# On crée les deux colonnes principales
col_left, col_right = st.columns([1, 1.2], gap="large")

# --- COLONNE GAUCHE : SAISIE ---
with col_left:
    st.subheader("⚙️ Console de Saisie")
    
    # Gestion ROI en Sidebar ou en haut de colonne
    roi = (((st.session_state.total_gains - st.session_state.total_mises) / st.session_state.total_mises) * 100) if st.session_state.total_mises > 0 else 0.0
    st.markdown(f'<div class="roi-card"><b>ROI : {roi:.1f}%</b> | Net : {st.session_state.total_gains - st.session_state.total_mises:.2f}€</div>', unsafe_allow_html=True)
    
    st.session_state.bankroll = st.number_input("💰 Capital (€)", value=st.session_state.bankroll)
    
    raw_data = st.text_area("📋 Coller données Zeturf", height=350, key="input_v11", placeholder="Collez le bloc ici...")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 ANALYSER"):
            if raw_data:
                df = extraire_donnees_v11(raw_data)
                if not df.empty:
                    st.session_state.current_df = df
                else: st.error("Format non reconnu.")
    with c2:
        if st.button("🗑️ VIDER"):
            st.session_state["input_v11"] = ""
            st.session_state.pop('current_df', None)
            st.rerun()

# --- COLONNE DROITE : RÉSULTATS ---
with col_right:
    st.subheader("📊 Résultats d'Analyse")
    
    if 'current_df' in st.session_state:
        df = st.session_state.current_df
        res_list = []
        for _, r in df.iterrows():
            p_estim = (1 / r['cote']) * 1.17
            v = p_estim * r['cote']
            m = max(0, st.session_state.bankroll * ((p_estim * (r['cote']-1) - (1-p_estim)) / (r['cote']-1)) * 0.08)
            res_list.append({"num": r['num'], "nom": r['nom'], "cote": r['cote'], "v": v, "m": m, "prob": p_estim})

        ordre = sorted(res_list, key=lambda x: x['prob'], reverse=True)
        top = ordre[0]
        vals = [v for v in res_list if v['v'] > 1.05 and v['cote'] >= 1.5]

        # 1. FAVORI
        st.markdown(f'<div class="favori-glow"><h2 style="color:#fbbf24; margin:0;">#{top["num"]} {top["nom"]}</h2><p style="margin:0;">Cote : {top["cote"]} | IA : {top["prob"]*100:.1f}%</p></div>', unsafe_allow_html=True)

        # 2. MISES
        st.write("💰 **MISES SIMPLE GAGNANT :**")
        if vals:
            for v in sorted(vals, key=lambda x: x['v'], reverse=True):
                st.success(f"**#{v['num']} {v['nom']}** → **{v['m']:.2f}€**")
        else:
            st.warning("Aucune mise rentable détectée.")

        # 3. ORDRE D'ARRIVÉE ESTIMÉ (PODIUM)
        st.write("🏆 **PODIUM ESTIMÉ :**")
        podium_html = '<div class="podium-box">'
        for i, r in enumerate(ordre[:3]):
            medaille = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
            podium_html += f"<b>{medaille} #{r['num']} {r['nom']}</b><br>"
        podium_html += '</div>'
        st.markdown(podium_html, unsafe_allow_html=True)

        # 4. TICKET À COPIER
        st.write("🎫 **TICKET TOP 5 :**")
        st.code(" - ".join([r['num'] for r in ordre[:5]]))

        # 5. FORMULAIRE DE GAIN
        st.divider()
        with st.form("roi_v11"):
            st.write("📝 Enregistrer résultat")
            m_f = st.number_input("Mise totale", value=sum([v['m'] for v in vals]))
            g_o = st.number_input("Gain reçu", value=0.0)
            if st.form_submit_button("VALIDER"):
                st.session_state.total_mises += m_f
                st.session_state.total_gains += g_o
                st.session_state.bankroll += (g_o - m_f)
                st.rerun()
    else:
        st.info("En attente de saisie à gauche...")

st.divider()
st.caption("TurfMaster AI v11 - La vue en colonnes pour un trading plus rapide.")
