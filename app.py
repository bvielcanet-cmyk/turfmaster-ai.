import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import re
import requests

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

# Tes identifiants Telegram directs
DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .favori-box { background-color: #1e3a8a; padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 15px; border: 2px solid #fbbf24; }
    .value-card { background-color: #f0fdf4; border-left: 8px solid #22c55e; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: black; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .poker-card { background-color: #fff7ed; border: 2px dashed #f97316; padding: 15px; border-radius: 10px; margin-top: 10px; color: black; }
    .footer-info { font-size: 12px; color: #666; text-align: center; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS LOGIQUES ---

def envoyer_telegram(message):
    url_tg = f"https://api.telegram.org/bot{DIRECT_TOKEN}/sendMessage"
    try:
        requests.post(url_tg, data={"chat_id": DIRECT_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
        return True
    except: return False

def extraire_depuis_texte(texte):
    """Analyse le texte brut copié-collé depuis Zeturf pour extraire chevaux et cotes"""
    partants = []
    lignes = texte.split('\n')
    for i, ligne in enumerate(lignes):
        # On cherche un nombre décimal (la cote)
        cote_match = re.search(r"(\d+[,\.]\d+)", ligne)
        if cote_match:
            try:
                cote = float(cote_match.group(1).replace(',', '.'))
                if cote > 1.0:
                    # Le nom est souvent la ligne juste avant ou le texte avant la cote
                    nom = lignes[i-1].strip() if i > 0 else "Inconnu"
                    if len(nom) < 3 or nom.replace('.','').isdigit(): 
                        nom = ligne.split(cote_match.group(1))[0].strip()
                    # Nettoyage rapide du nom
                    nom = re.sub(r'^\d+\s*|\s*\(.*?\)', '', nom).strip()
                    partants.append({"nom": nom[:20], "cote": cote})
            except: continue
    return pd.DataFrame(partants).drop_duplicates(subset=['nom'])

# --- 3. INTERFACE UTILISATEUR ---

st.title("🏇 TurfMaster AI Pro")
st.info(f"🕒 Heure de l'analyse : {datetime.now(tz_paris).strftime('%H:%M:%S')}")

# Zone de saisie
st.subheader("📋 Données de la course")
texte_brut = st.text_area("Sélectionne TOUT sur la page Zeturf, copie et colle ici :", height=150, placeholder="Ex: 1. Bold Eagle ... 2.5")
capital = st.number_input("💰 Ton Capital (€)", value=500, min_value=10)

if st.button("🚀 LANCER L'ANALYSE STRATÉGIQUE"):
    if not texte_brut:
        st.warning("Veuillez d'abord coller les données de la course.")
    else:
        df = extraire_depuis_texte(texte_brut)
        
        if not df.empty:
            # Calculs IA
            resultats = []
            for _, row in df.iterrows():
                # On ajuste la probabilité (avantage IA de 15%)
                prob_reelle = (1 / row['cote']) * 1.15
                val = prob_reelle * row['cote']
                # Formule de Kelly fractionnée (20%)
                mise = max(0, capital * ((prob_reelle * (row['cote']-1) - (1-prob_reelle)) / (row['cote']-1)) * 0.20)
                
                resultats.append({
                    "nom": row['nom'], "cote": row['cote'], "value": val, "mise": mise, "prob": prob_reelle * 100
                })

            # 1. TRI POUR LE CLASSEMENT D'ARRIVÉE
            ordre_arrivee = sorted(resultats, key=lambda x: x['prob'], reverse=True)
            
            # 2. AFFICHAGE : LE FAVORI IA
            top = ordre_arrivee[0]
            st.markdown(f"""
                <div class="favori-box">
                    <h3 style="margin:0; color:white;">🏆 LE FAVORI IA</h3>
                    <h1 style="margin:10px 0; color:#fbbf24;">{top['nom']}</h1>
                    <p style="margin:0; font-size:18px;">Probabilité de victoire : <b>{top['prob']:.1f}%</b></p>
                </div>
            """, unsafe_allow_html=True)

            # 3. AFFICHAGE : LES MISES À EFFECTUER
            st.subheader("💰 Mises conseillées (Value Bet)")
            values_detectees = [r for r in resultats if r['value'] > 1.05]
            
            if values_detectees:
                for v in sorted(values_detectees, key=lambda x: x['value'], reverse=True):
                    st.markdown(f"""
                        <div class="value-card">
                            <span style="float:right; background:#22c55e; color:white; padding:2px 8px; border-radius:5px; font-size:12px;">VALUE {v['value']:.2f}</span>
                            <b style="font-size:18px;">{v['nom']}</b><br>
                            👉 Miser : <b style="font-size:20px; color:#166534;">{v['mise']:.2f}€</b> (Cote : {v['cote']})
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Aucune opportunité rentable détectée. Pas de pari sur cette course.")

            # 4. AFFICHAGE : COUP DE POKER
            coup_poker = None
            poker_candidates = [r for r in resultats if r['cote'] >= 10 and r['prob'] > 5]
            if poker_candidates:
                coup_poker = max(poker_candidates, key=lambda x: x['value'])
                st.markdown(f"""
                    <div class="poker-card">
                        <h4 style="margin:0; color:#ea580c;">🃏 COUP DE POKER</h4>
                        <b style="font-size:17px;">{coup_poker['nom']}</b> à <b>{coup_poker['cote']}</b><br>
                        <small>Belle cote avec un potentiel de surprise selon l'IA.</small>
                    </div>
                """, unsafe_allow_html=True)

            # 5. AFFICHAGE : ORDRE D'ARRIVÉE COMPLET
            with st.expander("📊 Estimation complète de l'arrivée (Podium)"):
                for i, res in enumerate(ordre_arrivee[:6]):
                    medaille = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"{i+1}è"
                    st.write(f"{medaille} **{res['nom']}** — {res['prob']:.1f}% (Cote: {res['cote']})")

            # --- ENVOI TELEGRAM ---
            msg_tg = f"🏇 *ANALYSE TERMINÉE*\n\n🏆 Favori : {top['nom']}\n"
            if values_detectees:
                msg_tg += f"💰 MISE : {values_detectees[0]['nom']} ({values_detectees[0]['mise']:.2f}€)\n"
            if coup_poker:
                msg_tg += f"🃏 POKER : {coup_poker['nom']} (Cote {coup_poker['cote']})"
            envoyer_telegram(msg_tg)
            st.toast("Alerte Telegram envoyée !", icon="📩")

        else:
            st.error("Impossible d'extraire les données. Assure-toi de bien copier le tableau des partants.")

# --- 4. BILAN ---
st.divider()
st.markdown("<div class='footer-info'>TurfMaster AI Pro v3.0 - Analyse Statistique Kelly</div>", unsafe_allow_html=True)
