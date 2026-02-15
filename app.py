import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import re
import requests

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro v5", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .favori-box { background-color: #1e3a8a; padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 15px; border: 2px solid #fbbf24; }
    .value-card { background-color: #f0fdf4; border-left: 8px solid #22c55e; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: black; }
    .num-badge { background-color: #333; color: white; padding: 4px 12px; border-radius: 8px; font-weight: bold; font-size: 20px; margin-right: 10px; border: 2px solid #fbbf24; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS LOGIQUES ---

def envoyer_telegram(message):
    url_tg = f"https://api.telegram.org/bot{DIRECT_TOKEN}/sendMessage"
    try: requests.post(url_tg, data={"chat_id": DIRECT_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def extraire_donnees_multi_lignes(texte):
    """Extrait les données quand Numéro, Nom et Cote sont sur des lignes séparées"""
    partants = []
    # On nettoie les espaces de début/fin sur chaque ligne
    lignes = [l.strip() for l in texte.split('\n') if l.strip()]
    
    i = 0
    while i < len(lignes):
        # 1. On cherche un numéro (chiffre seul sur une ligne)
        if lignes[i].isdigit() and 1 <= int(lignes[i]) <= 22:
            num = lignes[i]
            try:
                # 2. Le nom est normalement juste sur la ligne suivante
                nom = lignes[i+1].upper()
                
                # 3. On cherche la cote dans les 5 lignes suivantes
                # (Zeturf met souvent la cote après la musique/distance)
                cote = None
                for j in range(2, 6):
                    if i + j < len(lignes):
                        potentiell_cote = lignes[i+j].replace(',', '.')
                        # On vérifie si c'est un nombre avec décimale (ex: 12.1)
                        if re.match(r"^\d+\.\d+$", potentiell_cote):
                            cote = float(potentiell_cote)
                            i = i + j # On avance l'index après la cote
                            break
                
                if num and nom and cote:
                    partants.append({"num": num, "nom": nom, "cote": cote})
            except:
                pass
        i += 1
    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI Pro")
st.info(f"🕒 Analyse du {datetime.now(tz_paris).strftime('%H:%M:%S')}")

texte_brut = st.text_area("Colle ici le bloc Zeturf (Numéro, Nom, Détails, Cote) :", height=250)
capital = st.number_input("💰 Capital (€)", value=500, min_value=10)

if st.button("🚀 ANALYSER LA COURSE"):
    if not texte_brut:
        st.warning("Veuillez coller les données de la course.")
    else:
        df = extraire_donnees_multi_lignes(texte_brut)
        
        if not df.empty:
            resultats = []
            for _, row in df.iterrows():
                p = (1 / row['cote']) * 1.15
                v = p * row['cote']
                m = max(0, capital * ((p * (row['cote']-1) - (1-p)) / (row['cote']-1)) * 0.20)
                resultats.append({"num": row['num'], "nom": row['nom'], "cote": row['cote'], "value": v, "mise": m, "prob": p * 100})

            ordre = sorted(resultats, key=lambda x: x['prob'], reverse=True)
            
            # Affichage Ticket
            st.subheader("🎫 Ticket à copier")
            ticket = " - ".join([r['num'] for r in ordre[:5]])
            st.code(ticket, language="text")

            # Affichage Favori
            top = ordre[0]
            st.markdown(f"""
                <div class="favori-box">
                    <h3 style="margin:0; color:white;">🏆 FAVORI IA</h3>
                    <h1 style="margin:10px 0; color:#fbbf24;"><span style="color:white;">#{top['num']}</span> {top['nom']}</h1>
                    <p style="margin:0; font-size:18px;">Probabilité : <b>{top['prob']:.1f}%</b></p>
                </div>
            """, unsafe_allow_html=True)

            # Affichage Mises
            st.subheader("💰 Mises conseillées")
            vals = [r for r in resultats if r['value'] > 1.05]
            if vals:
                for v in sorted(vals, key=lambda x: x['value'], reverse=True):
                    st.markdown(f"""
                        <div class="value-card">
                            <span class="num-badge">{v['num']}</span> <b>{v['nom']}</b><br>
                            <span style="font-size:19px; color:#166534;">Miser : <b>{v['mise']:.2f}€</b></span> (Cote: {v['cote']})
                        </div>
                    """, unsafe_allow_html=True)
            else: st.info("Pas de value détectée.")

            # Telegram
            envoyer_telegram(f"🏇 *ANALYSE OK*\nTicket: `{ticket}`\nFavori: #{top['num']} {top['nom']}")
        else:
            st.error("❌ Impossible de lire le format. Assure-toi d'avoir copié le numéro, le nom et la cote.")
