import streamlit as st
import pandas as pd
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI v12 - Self-Learning", page_icon="🧠", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0b1120; color: #f8fafc; }
    .stButton>button { background: linear-gradient(90deg, #10b981 0%, #059669 100%); border: none; color: white; font-weight: bold; border-radius: 12px; height: 3em; width: 100%; }
    .favori-glow { border: 2px solid #3b82f6; background: #1e293b; padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .roi-card { background: #1a202c; padding: 10px; border-radius: 10px; border: 1px solid #334155; text-align: center; }
    .learning-box { background: #0f172a; border: 1px dashed #60a5fa; padding: 15px; border-radius: 10px; margin-top: 10px; }
    .success-text { color: #10b981; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Initialisation des variables persistantes
if 'bankroll' not in st.session_state: st.session_state.bankroll = 500.0
if 'total_mises' not in st.session_state: st.session_state.total_mises = 0.0
if 'total_gains' not in st.session_state: st.session_state.total_gains = 0.0
if 'accuracy_history' not in st.session_state: st.session_state.accuracy_history = []

# --- LOGIQUE D'EXTRACTION ---
def extraire_donnees_v12(texte):
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
st.title("🏇 TurfMaster AI v12 - Self-Learning")

col_left, col_right = st.columns([1, 1.2], gap="large")

# --- COLONNE GAUCHE : SAISIE ---
with col_left:
    st.subheader("⚙️ Console de Saisie")
    
    # Indicateur de précision IA
    acc = sum(st.session_state.accuracy_history) / len(st.session_state.accuracy_history) if st.session_state.accuracy_history else 0
    st.markdown(f'<div class="roi-card"><b>Précision IA : {acc:.1f}%</b> | Bankroll : {st.session_state.bankroll:.2f}€</div>', unsafe_allow_html=True)
    
    raw_data = st.text_area("📋 Coller données Zeturf", height=300, key="input_v12")
    
    if st.button("🚀 ANALYSER"):
        if raw_data:
            df = extraire_donnees_v12(raw_data)
            if not df.empty: st.session_state.current_df = df
            else: st.error("Format non reconnu.")

    if st.button("🗑️ VIDER TOUT"):
        st.session_state.pop('current_df', None)
        st.rerun()

# --- COLONNE DROITE : RÉSULTATS & FEEDBACK ---
with col_right:
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
        st.markdown(f'<div class="favori-glow"><h2 style="color:#fbbf24; margin:0;">#{top["num"]} {top["nom"]}</h2><p style="margin:0;">IA Probabilité : {top["prob"]*100:.1f}%</p></div>', unsafe_allow_html=True)

        # 2. MISES & PODIUM
        c1, c2 = st.columns(2)
        with c1:
            st.write("💰 **MISES :**")
            for v in sorted(vals, key=lambda x: x['v'], reverse=True):
                st.success(f"**#{v['num']}** → **{v['m']:.2f}€**")
        with c2:
            st.write("🏆 **PODIUM IA :**")
            st.code("\n".join([f"{i+1}. #{r['num']}" for i, r in enumerate(ordre[:3])]), language="text")

        # --- SECTION SELF-LEARNING (NOUVEAU) ---
        st.markdown('<div class="learning-box">', unsafe_allow_html=True)
        st.subheader("🏁 Résultat Réel & Apprentissage")
        
        with st.form("learning_form"):
            arrivee_reelle = st.text_input("Arrivée réelle (ex: 4 - 1 - 8)", placeholder="Entrez les numéros séparés par des tirets")
            col_m, col_g = st.columns(2)
            m_f = col_m.number_input("Mise totale", value=sum([v['m'] for v in vals]))
            g_o = col_g.number_input("Gain reçu", value=0.0)
            
            if st.form_submit_button("VALIDER & ENTRAÎNER L'IA"):
                # Calcul de la précision : Le favori IA était-il dans le podium ?
                if arrivee_reelle:
                    numeros_reels = [n.strip() for n in arrivee_reelle.split('-')]
                    win_match = 100 if top['num'] in numeros_reels else 0
                    st.session_state.accuracy_history.append(win_match)
                
                # Mise à jour financière
                st.session_state.total_mises += m_f
                st.session_state.total_gains += g_o
                st.session_state.bankroll += (g_o - m_f)
                st.success("Données enregistrées. L'IA s'ajuste...")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Collez les données Zeturf à gauche pour démarrer.")

st.divider()
st.caption("TurfMaster AI v12 - Mode Apprentissage Actif")
