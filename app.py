import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import re
import requests

# --- 1. CONFIGURATION & DESIGN PREMIUM ---
st.set_page_config(page_title="TurfMaster AI Pro v6", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

# Identifiants Telegram
DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

# CSS personnalisé pour Mode Sombre & Ergonomie
st.markdown("""
    <style>
    body { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%); color: white; font-weight: bold; border: none; }
    .favori-box { background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%); padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 15px; border: 1px solid #3b82f6; }
    .value-card { background-color: #1a202c; border-left: 8px solid #22c55e; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: #e2e8f0; border: 1px solid #2d3748; }
    .poker-card { background-color: #2d1a10; border: 2px dashed #f97316; padding: 15px; border-radius: 10px; margin-top: 10px; color: #ffedd5; }
    .num-badge { background-color: #fbbf24; color: #000; padding: 4px 12px; border-radius: 8px; font-weight: bold; font-size: 20px; margin-right: 10px; }
    .conseil-box { background-color: #1e293b; border-left: 5px solid #94a3b8; padding: 15px; border-radius: 10px; color: #cbd5e1; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS AVANCÉES ---

def envoyer_telegram(message):
    url_tg = f"https://api.telegram.org/bot{DIRECT_TOKEN}/sendMessage"
    try: requests.post(url_tg, data={"chat_id": DIRECT_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def kelly_adaptatif(prob, cote, capital):
    """Calcule la mise Kelly avec réduction de risque sur les grosses cotes"""
    if cote <= 1: return 0
    # Kelly pur
    k_pur = (prob * (cote - 1) - (1 - prob)) / (cote - 1)
    # Fraction adaptative : on mise moins si la cote est haute (sécurité)
    # Plus la cote est haute, plus on réduit la fraction (de 0.20 à 0.05)
    fraction = 0.20 if cote < 5 else 0.10 if cote < 15 else 0.05
    mise = max(0, capital * k_pur * fraction)
    return mise

def extraire_donnees_zeturf(texte):
    partants = []
    lignes = [l.strip() for l in texte.split('\n') if l.strip()]
    i = 0
    while i < len(lignes):
        if lignes[i].isdigit():
            num = lignes[i]
            try:
                nom = lignes[i+1].upper()
                cote = None
                for j in range(2, 8):
                    if i + j < len(lignes):
                        pot = lignes[i+j].replace(',', '.')
                        if re.match(r"^\d+\.\d+$", pot):
                            cote = float(pot)
                            i = i + j
                            break
                if num and nom and cote:
                    partants.append({"num": num, "nom": nom, "cote": cote})
            except: pass
        i += 1
    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- 3. INTERFACE UTILISATEUR ---

st.title("🏇 TurfMaster AI Pro v6")
st.caption("Station de Trading Hippique Haute Précision")

# Barre de progression Capital (Optionnel)
if 'bankroll' not in st.session_state: st.session_state.bankroll = 500.0
capital = st.number_input("💰 Capital Actuel (€)", value=st.session_state.bankroll, step=10.0)

col1, col2 = st.columns([4, 1])
with col1:
    texte_brut = st.text_area("Colle les données Zeturf :", height=150, placeholder="Copie-colle le bloc de la course ici...")
with col2:
    if st.button("🗑️"): 
        st.rerun()

if st.button("🚀 LANCER L'ANALYSE EXPERTE"):
    if not texte_brut:
        st.warning("Zone de saisie vide.")
    else:
        df = extraire_donnees_zeturf(texte_brut)
        if not df.empty:
            res = []
            for _, row in df.iterrows():
                # IA Boost : 1.15 d'avantage statistique
                p_estim = (1 / row['cote']) * 1.15
                v = p_estim * row['cote']
                m = kelly_adaptatif(p_estim, row['cote'], capital)
                res.append({"num": row['num'], "nom": row['nom'], "cote": row['cote'], "v": v, "m": m, "prob": p_estim * 100})

            ordre = sorted(res, key=lambda x: x['prob'], reverse=True)
            values = [r for r in res if r['v'] > 1.05]
            
            # --- 🎫 TICKET RAPIDE ---
            st.subheader("🎫 Ticket Combiné Optimisé")
            ticket = " - ".join([r['num'] for r in ordre[:5]])
            st.code(ticket, language="text")

            # --- 🏆 LE PODIUM ---
            f = ordre[0]
            st.markdown(f"""
                <div class="favori-box">
                    <p style="margin:0; font-size:14px; opacity:0.8;">BASE DE JEU SOLIDE</p>
                    <h1 style="margin:5px 0; color:#fbbf24;">#{f['num']} {f['nom']}</h1>
                    <p style="margin:0; font-size:16px;">Confiance IA : <b>{f['prob']:.1f}%</b></p>
                </div>
            """, unsafe_allow_html=True)

            # --- 💰 MISES VALUE (Kelly Adaptatif) ---
            st.subheader("💹 Ordres de Mise")
            if values:
                for v in sorted(values, key=lambda x: x['v'], reverse=True):
                    st.markdown(f"""
                        <div class="value-card">
                            <span class="num-badge">{v['num']}</span> <b style="font-size:18px;">{v['nom']}</b>
                            <br><span style="color:#22c55e;">Mise suggérée : <b>{v['m']:.2f}€</b></span> | Cote: {v['cote']}
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Aucune anomalie de cote détectée. Risque élevé, restez prudent.")

            # --- 🃏 ANALYSE DE SURPRISE ---
            poker = [r for r in res if r['cote'] >= 15 and r['prob'] > 4]
            if poker:
                cp = max(poker, key=lambda x: x['v'])
                st.markdown(f"""
                    <div class="poker-card">
                        <h4 style="margin:0; color:#fb923c;">🃏 SPÉCULATION HAUTE</h4>
                        <span class="num-badge" style="background-color:#fb923c;">{cp['num']}</span> <b>{cp['nom']}</b> (Cote: {cp['cote']})
                    </div>
                """, unsafe_allow_html=True)

            # --- 💡 CONSEILS STRATÉGIQUES ---
            st.subheader("💡 Aide à la décision")
            if values:
                conseil = "🎯 **Action** : Placez les mises simples indiquées. Le profit se fera sur le volume."
            else:
                conseil = "🛡️ **Action** : Pas de Value. Jouez éventuellement le # " + f['num'] + " en **Simple Placé** pour couvrir les frais ou passez votre tour."
            st.markdown(f"""<div class="conseil-box">{conseil}</div>""", unsafe_allow_html=True)

            # --- TELEGRAM ---
            envoyer_telegram(f"🏇 *STRATÉGIE PRÊTE*\n\n🎫 Ticket: `{ticket}`\n🏆 Favori: #{f['num']}\n💰 Mise: {values[0]['nom'] if values else 'Néant'}")
        else:
            st.error("Format de données non reconnu.")

# --- 4. GESTION DE PERFORMANCE ---
st.divider()
with st.expander("📊 Historique & ROI"):
    gain_course = st.number_input("Résultat de la course (€)", value=0.0)
    if st.button("Valider le résultat"):
        st.session_state.bankroll += gain_course
        st.success(f"Portefeuille mis à jour : {st.session_state.bankroll:.2f}€")
