import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import re
import requests

# --- 1. CONFIGURATION & DESIGN ---
st.set_page_config(page_title="TurfMaster AI Pro v4.5", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

# Identifiants Telegram
DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .favori-box { background-color: #1e3a8a; padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 15px; border: 2px solid #fbbf24; }
    .value-card { background-color: #f0fdf4; border-left: 8px solid #22c55e; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: black; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .num-badge { background-color: #333; color: white; padding: 4px 12px; border-radius: 8px; font-weight: bold; font-size: 20px; margin-right: 10px; border: 2px solid #fbbf24; }
    .poker-card { background-color: #fff7ed; border: 2px dashed #f97316; padding: 15px; border-radius: 10px; margin-top: 10px; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS LOGIQUES ---

def envoyer_telegram(message):
    url_tg = f"https://api.telegram.org/bot{DIRECT_TOKEN}/sendMessage"
    try:
        requests.post(url_tg, data={"chat_id": DIRECT_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def extraire_depuis_texte(texte):
    """Extraction FORCÉE : Numéro (début) -> Nom (MAJ) -> Cote (Décimale)"""
    partants = []
    # Nettoyage des espaces multiples
    texte = re.sub(r' +', ' ', texte)
    
    # REGEX FORCÉE :
    # ^(\d{1,2})           : Un numéro (1 ou 2 chiffres) en début de ligne
    # \s+                  : Un ou plusieurs espaces
    # ([A-ZÀ-Ÿ\s\-']{3,})  : Le nom en MAJUSCULES (lettres, espaces, tirets)
    # .*?                  : N'importe quel texte entre (jockey, etc.)
    # (\d+[,\.]\d+)        : OBLIGATOIREMENT une cote avec décimale (ex: 4.5 ou 4,5)
    pattern = re.compile(r"^(\d{1,2})\s+([A-ZÀ-Ÿ\s\-']{3,50}?).*?(\d+[,\.]\d+)", re.MULTILINE)

    matches = pattern.findall(texte)

    for m in matches:
        try:
            num = m[0]
            nom = m[1].strip()
            # On prend le premier mot ou groupe de mots en majuscules pour éviter de déborder sur le jockey
            nom = re.split(r'\s{2,}', nom)[0].strip() 
            cote = float(m[2].replace(',', '.'))
            
            if cote > 1.0:
                partants.append({"num": num, "nom": nom, "cote": cote})
        except:
            continue

    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI Pro")
st.info(f"🕒 Analyse du {datetime.now(tz_paris).strftime('%H:%M:%S')}")

texte_brut = st.text_area("Colle ici le tableau Zeturf :", height=200, placeholder="Exemple attendu :\n1 BOLD EAGLE ... 4.5\n2 FACE TIME ... 1.8")
capital = st.number_input("💰 Capital (€)", value=500, min_value=10)

if st.button("🚀 ANALYSER LA COURSE"):
    if not texte_brut:
        st.warning("Veuillez coller les données.")
    else:
        df = extraire_depuis_texte(texte_brut)
        
        if not df.empty:
            resultats = []
            for _, row in df.iterrows():
                # Probabilité ajustée avec marge IA (15%)
                p = (1 / row['cote']) * 1.15
                v = p * row['cote']
                m = max(0, capital * ((p * (row['cote']-1) - (1-p)) / (row['cote']-1)) * 0.20)
                
                resultats.append({
                    "num": row['num'], "nom": row['nom'], "cote": row['cote'], "value": v, "mise": m, "prob": p * 100
                })

            ordre = sorted(resultats, key=lambda x: x['prob'], reverse=True)
            
            # --- AFFICHAGE ---
            
            # Ticket Rapide
            st.subheader("🎫 Ticket à copier")
            ticket = " - ".join([r['num'] for r in ordre[:5]])
            st.code(ticket, language="text")

            # Favori
            top = ordre[0]
            st.markdown(f"""
                <div class="favori-box">
                    <h3 style="margin:0; color:white;">🏆 PREMIER DU CLASSEMENT</h3>
                    <h1 style="margin:10px 0; color:#fbbf24;"><span style="color:white;">#{top['num']}</span> {top['nom']}</h1>
                    <p style="margin:0; font-size:18px;">Probabilité : <b>{top['prob']:.1f}%</b></p>
                </div>
            """, unsafe_allow_html=True)

            # Mises
            st.subheader("💰 Mises conseillées")
            vals = [r for r in resultats if r['value'] > 1.05]
            if vals:
                for v in sorted(vals, key=lambda x: x['value'], reverse=True):
                    st.markdown(f"""
                        <div class="value-card">
                            <span class="num-badge">{v['num']}</span> <b style="font-size:18px;">{v['nom']}</b><br>
                            <span style="font-size:19px; color:#166534;">Miser : <b>{v['mise']:.2f}€</b></span> (Cote: {v['cote']})
                        </div>
                    """, unsafe_allow_html=True)
            else: st.info("Aucune mise rentable détectée.")

            # Poker
            poker = [r for r in resultats if r['cote'] >= 12 and r['prob'] > 4]
            if poker:
                cp = max(poker, key=lambda x: x['value'])
                st.markdown(f"""<div class="poker-card"><h4>🃏 COUP DE POKER</h4><span class="num-badge">{cp['num']}</span> <b>{cp['nom']}</b> (Cote: {cp['cote']})</div>""", unsafe_allow_html=True)

            # Envoi Telegram
            envoyer_telegram(f"🏇 *COURSE ANALYSÉE*\n🎫 Ticket : `{ticket}`\n🏆 Favori : #{top['num']} {top['nom']}")
            
        else:
            st.error("❌ Analyse impossible. Assurez-vous que chaque ligne commence par le NUMÉRO et contient une COTE avec virgule ou point.")
