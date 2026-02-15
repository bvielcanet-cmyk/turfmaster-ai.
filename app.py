import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import re
import requests

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro v5.2", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .favori-box { background-color: #1e3a8a; padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 15px; border: 2px solid #fbbf24; }
    .value-card { background-color: #f0fdf4; border-left: 8px solid #22c55e; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: black; }
    .num-badge { background-color: #333; color: white; padding: 4px 12px; border-radius: 8px; font-weight: bold; font-size: 20px; margin-right: 10px; border: 2px solid #fbbf24; }
    .conseil-box { background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 10px; margin-top: 10px; color: #1e293b; font-size: 14px; border-left: 5px solid #64748b; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS ---

def envoyer_telegram(message):
    url_tg = f"https://api.telegram.org/bot{DIRECT_TOKEN}/sendMessage"
    try: requests.post(url_tg, data={"chat_id": DIRECT_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def extraire_donnees_zeturf(texte):
    partants = []
    lignes = [l.strip() for l in texte.split('\n') if l.strip()]
    i = 0
    while i < len(lignes):
        if lignes[i].isdigit() and 1 <= int(lignes[i]) <= 24:
            num = lignes[i]
            try:
                nom = lignes[i+1].upper()
                cote = None
                for j in range(2, 7):
                    if i + j < len(lignes):
                        pot = lignes[i+j].replace(',', '.')
                        if re.match(r"^\d+\.\d+$", pot) or (pot.isdigit() and int(pot) > 1):
                            cote = float(pot)
                            i = i + j
                            break
                if num and nom and cote:
                    partants.append({"num": num, "nom": nom, "cote": cote})
            except: pass
        i += 1
    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI Pro")
st.info(f"🕒 Analyse en temps réel : {datetime.now(tz_paris).strftime('%H:%M:%S')}")

texte_brut = st.text_area("Colle les données de la course ici :", height=200)
capital = st.number_input("💰 Capital total (€)", value=500, min_value=10)

if st.button("🚀 ANALYSER ET GÉNÉRER LA STRATÉGIE"):
    if not texte_brut:
        st.warning("Veuillez coller des données.")
    else:
        df = extraire_donnees_zeturf(texte_brut)
        if not df.empty:
            res = []
            for _, row in df.iterrows():
                p = (1 / row['cote']) * 1.15
                v = p * row['cote']
                m = max(0, capital * ((p * (row['cote']-1) - (1-p)) / (row['cote']-1)) * 0.20)
                res.append({"num": row['num'], "nom": row['nom'], "cote": row['cote'], "v": v, "m": m, "prob": p * 100})

            ordre = sorted(res, key=lambda x: x['prob'], reverse=True)
            values = [r for r in res if r['v'] > 1.05]
            
            # TICKET RAPIDE
            st.subheader("🎫 Ticket à copier")
            ticket = " - ".join([r['num'] for r in ordre[:5]])
            st.code(ticket, language="text")

            # FAVORI IA
            f = ordre[0]
            st.markdown(f"""<div class="favori-box"><h3>🏆 FAVORI IA</h3><h1>#{f['num']} {f['nom']}</h1><b>Confiance : {f['prob']:.1f}%</b></div>""", unsafe_allow_html=True)

            # MISES
            st.subheader("💰 Mises conseillées")
            if values:
                for v in sorted(values, key=lambda x: x['v'], reverse=True):
                    st.markdown(f"""<div class="value-card"><span class="num-badge">{v['num']}</span> <b>{v['nom']}</b><br>Miser : <b>{v['m']:.2f}€</b> (Cote: {v['cote']})</div>""", unsafe_allow_html=True)
            else: st.info("Aucune mise rentable.")

            # --- 💡 SECTION CONSEILS DE PARIS ---
            st.subheader("💡 Conseils Stratégiques")
            conseil = ""
            if values:
                if len(values) >= 2:
                    conseil = "🎯 **Stratégie Combinée** : Jouez les chevaux indiqués en **Simple Gagnant**. Pour un ticket plus rémunérateur, tentez un **Couplé Gagnant** avec les numéros du ticket à copier."
                else:
                    conseil = "💎 **Pari de Valeur Unique** : Un seul cheval présente un avantage. Concentrez votre mise sur le **N°" + values[0]['num'] + "** en Simple Gagnant."
            else:
                conseil = "⚠️ **Prudence** : Les cotes actuelles sont trop justes. Si vous voulez jouer, privilégiez un petit **Simple Placé** sur le Favori IA ou passez votre tour."
            
            st.markdown(f"""<div class="conseil-box">{conseil}</div>""", unsafe_allow_html=True)

            # Telegram
            envoyer_telegram(f"🏇 *ANALYSE OK*\nTicket: `{ticket}`\nFavori: #{f['num']} {f['nom']}")
        else:
            st.error("Données illisibles. Vérifie le format.")
