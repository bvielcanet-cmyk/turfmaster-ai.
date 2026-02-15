import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import re
import requests

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro v6.1", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')
DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

st.markdown("""
    <style>
    body { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%); color: white; font-weight: bold; }
    .favori-box { background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%); padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 15px; border: 1px solid #3b82f6; }
    .value-card { background-color: #1a202c; border-left: 8px solid #22c55e; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: #e2e8f0; border: 1px solid #2d3748; }
    .num-badge { background-color: #fbbf24; color: #000; padding: 4px 12px; border-radius: 8px; font-weight: bold; font-size: 20px; margin-right: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE D'EXTRACTION "SANS ÉCHEC" ---

def extraire_donnees_flex(texte):
    """Cherche des séquences (Numéro -> Nom -> Cote) peu importe les lignes."""
    partants = []
    # Nettoie le texte : remplace les virgules par des points et normalise les espaces
    texte = texte.replace(',', '.')
    
    # On cherche le numéro (1 à 22) suivi par du texte (le nom) et finit par une cote (chiffre.chiffre)
    # Cette regex scanne tout le bloc sans se soucier des retours à la ligne
    pattern = re.compile(r"(\b\d{1,2}\b)\s+([A-ZÀ-Ÿ\s\-']{3,60}?).*?(\d+\.\d+)", re.DOTALL)
    
    matches = pattern.finditer(texte)
    
    for m in matches:
        num = m.group(1).strip()
        nom_brut = m.group(2).strip()
        cote_brut = m.group(3).strip()
        
        # Nettoyage du nom (on garde les majuscules seulement)
        nom = " ".join(re.findall(r"\b[A-ZÀ-Ÿ]{3,}\b", nom_brut))
        if not nom: nom = nom_brut.split('\n')[0] # Fallback
        
        try:
            cote = float(cote_brut)
            if cote > 1.0 and int(num) < 25:
                partants.append({"num": num, "nom": nom[:20], "cote": cote})
        except: continue

    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- RESTE DE L'INTERFACE ---

st.title("🏇 TurfMaster AI Pro")
if 'bankroll' not in st.session_state: st.session_state.bankroll = 500.0
capital = st.number_input("💰 Capital (€)", value=st.session_state.bankroll)

texte_brut = st.text_area("Colle ici les données Zeturf (tout le bloc) :", height=200)

if st.button("🚀 ANALYSER LA COURSE"):
    if not texte_brut:
        st.warning("Veuillez coller les données.")
    else:
        df = extraire_donnees_flex(texte_brut)
        
        if not df.empty:
            res = []
            for _, row in df.iterrows():
                p = (1 / row['cote']) * 1.15
                v = p * row['cote']
                # Kelly Adaptatif
                fraction = 0.20 if row['cote'] < 5 else 0.10 if row['cote'] < 15 else 0.05
                m = max(0, capital * ((p * (row['cote']-1) - (1-p)) / (row['cote']-1)) * fraction)
                res.append({"num": row['num'], "nom": row['nom'], "cote": row['cote'], "v": v, "m": m, "prob": p * 100})

            ordre = sorted(res, key=lambda x: x['prob'], reverse=True)
            
            # --- AFFICHAGE ---
            st.subheader("🎫 Ticket : " + " - ".join([r['num'] for r in ordre[:5]]))
            
            f = ordre[0]
            st.markdown(f"""<div class="favori-box"><h3>🏆 FAVORI IA</h3><h1>#{f['num']} {f['nom']}</h1><b>Confiance : {f['prob']:.1f}%</b></div>""", unsafe_allow_html=True)

            st.subheader("💰 Mises conseillées")
            vals = [r for r in res if r['v'] > 1.05]
            if vals:
                for v in sorted(vals, key=lambda x: x['v'], reverse=True):
                    st.markdown(f"""<div class="value-card"><span class="num-badge">{v['num']}</span><b>{v['nom']}</b><br>Miser : <b style="color:#22c55e;">{v['m']:.2f}€</b> (Cote: {v['cote']})</div>""", unsafe_allow_html=True)
            else: st.info("Aucune opportunité rentable.")
            
            # Telegram
            requests.post(f"https://api.telegram.org/bot{DIRECT_TOKEN}/sendMessage", data={"chat_id": DIRECT_CHAT_ID, "text": f"🏇 #{f['num']} {f['nom']} analysé !"})
        else:
            st.error("❌ Échec : Format non reconnu.")
            st.write("Vérifie que ton copier-coller contient bien le numéro, le nom et la cote (ex: 12.5).")
