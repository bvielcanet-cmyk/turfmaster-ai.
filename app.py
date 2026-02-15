import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import re
import requests

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .favori-box { background-color: #1e3a8a; padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 15px; border: 2px solid #fbbf24; }
    .value-card { background-color: #f0fdf4; border-left: 8px solid #22c55e; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: black; }
    .num-badge { background-color: #333; color: white; padding: 4px 10px; border-radius: 8px; font-weight: bold; font-size: 18px; margin-right: 10px; border: 1px solid #fbbf24; }
    .ticket-box { background-color: #f8fafc; border: 1px solid #cbd5e1; padding: 15px; border-radius: 10px; text-align: center; font-family: monospace; font-size: 20px; color: #1e293b; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS ---

def envoyer_telegram(message):
    url_tg = f"https://api.telegram.org/bot{DIRECT_TOKEN}/sendMessage"
    try: requests.post(url_tg, data={"chat_id": DIRECT_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def extraire_depuis_texte(texte):
    partants = []
    lignes = texte.split('\n')
    for i, ligne in enumerate(lignes):
        cote_match = re.search(r"(\d+[,\.]\d+)", ligne)
        if cote_match:
            try:
                cote = float(cote_match.group(1).replace(',', '.'))
                # Extraction améliorée du numéro (début de ligne ou entouré d'espaces)
                num_match = re.search(r"\b(\d{1,2})\b", ligne)
                numero = num_match.group(1) if num_match else "?"
                
                nom_brut = lignes[i-1].strip() if i > 0 else "Inconnu"
                if len(nom_brut) < 3 or nom_brut.isdigit():
                    nom_brut = ligne.split(cote_match.group(1))[0].replace(numero, "").strip()
                
                nom = re.sub(r'[^a-zA-Z\s]', '', nom_brut).strip()
                partants.append({"num": numero, "nom": nom[:20], "cote": cote})
            except: continue
    return pd.DataFrame(partants).drop_duplicates(subset=['nom'])

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI Pro")
st.info(f"🕒 {datetime.now(tz_paris).strftime('%H:%M:%S')}")

texte_brut = st.text_area("Colle les données Zeturf ici :", height=150)
capital = st.number_input("💰 Capital (€)", value=500)

if st.button("🚀 ANALYSER LA COURSE"):
    if not texte_brut:
        st.warning("Colle d'abord les chevaux !")
    else:
        df = extraire_depuis_texte(texte_brut)
        if not df.empty:
            resultats = []
            for _, row in df.iterrows():
                p = (1 / row['cote']) * 1.15
                v = p * row['cote']
                m = max(0, capital * ((p * (row['cote']-1) - (1-p)) / (row['cote']-1)) * 0.20)
                resultats.append({"num": row['num'], "nom": row['nom'], "cote": row['cote'], "value": v, "m": m, "prob": p * 100})

            ordre = sorted(resultats, key=lambda x: x['prob'], reverse=True)
            
            # --- TICKET RAPIDE ---
            st.subheader("🎫 Ton Ticket à copier")
            top_nums = " - ".join([r['num'] for r in ordre[:5]]) # Top 5
            st.code(top_nums, language="text")
            st.caption("Cliquer sur l'icône à droite pour copier la liste des numéros")

            # --- FAVORI ---
            f = ordre[0]
            st.markdown(f"""<div class="favori-box"><h3>🏆 FAVORI</h3><h1><span style="color:#fbbf24;">N°{f['num']}</span> {f['nom']}</h1><b>{f['prob']:.1f}% de chance</b></div>""", unsafe_allow_html=True)

            # --- MISES ---
            st.subheader("💰 Mises Value")
            vals = [r for r in resultats if r['value'] > 1.05]
            if vals:
                for v in sorted(vals, key=lambda x: x['value'], reverse=True):
                    st.markdown(f"""<div class="value-card"><span class="num-badge">{v['num']}</span> <b>{v['nom']}</b><br>Miser : <b>{v['m']:.2f}€</b> (Cote: {v['cote']})</div>""", unsafe_allow_html=True)
            else: st.write("Pas de value détectée.")

            # --- PODIUM ---
            with st.expander("📊 Arrivée estimée"):
                for i, r in enumerate(ordre[:6]):
                    st.write(f"{i+1}. **#{r['num']}** {r['nom']} ({r['prob']:.1f}%)")

            # TELEGRAM
            msg = f"🏇 *COURSE ANALYSÉE*\n\n🎫 Ticket : `{top_nums}`\n🏆 Favori : N°{f['num']} {f['nom']}"
            envoyer_telegram(msg)
        else:
            st.error("Données illisibles.")
