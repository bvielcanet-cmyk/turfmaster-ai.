import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import re
import requests

# --- CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇")
tz_paris = pytz.timezone('Europe/Paris')

# Tes identifiants
DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

st.markdown("""<style>.card { background-color: #f9f9f9; border-radius: 10px; padding: 15px; margin-bottom: 10px; border-left: 5px solid #28a745; color: black; }</style>""", unsafe_allow_html=True)

def envoyer_telegram(message):
    url_tg = f"https://api.telegram.org/bot{DIRECT_TOKEN}/sendMessage"
    try: requests.post(url_tg, data={"chat_id": DIRECT_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def extraire_depuis_texte(texte):
    """Analyse le texte brut copié-collé depuis Zeturf"""
    partants = []
    # On cherche les motifs type "Nom du cheval" suivi d'un chiffre (cote)
    # Fonctionne même avec un copier-coller sale
    lignes = texte.split('\n')
    for i, ligne in enumerate(lignes):
        # Recherche d'une cote (ex: 4,5 ou 12.0)
        cote_match = re.search(r"(\d+[,\.]\d+)", ligne)
        if cote_match:
            cote = float(cote_match.group(1).replace(',', '.'))
            if cote > 1.0:
                # Le nom est souvent juste au-dessus ou sur la même ligne
                nom = lignes[i-1].strip() if i > 0 else "Cheval"
                if len(nom) < 3: nom = ligne.split(cote_match.group(1))[0].strip()
                partants.append({"nom": nom[:20], "cote": cote})
    return pd.DataFrame(partants).drop_duplicates(subset=['nom'])

# --- INTERFACE ---
st.title("🏇 TurfMaster AI (Mode Secours)")
st.info(f"🕒 {datetime.now(tz_paris).strftime('%H:%M:%S')}")

tab1, tab2 = st.tabs(["📋 Copier-Coller (Sûr)", "🔗 URL (Si non bloqué)"])

with tab1:
    st.write("1. Va sur Zeturf\n2. Sélectionne tout le tableau des partants\n3. Colle-le ici :")
    texte_brut = st.text_area("Coller les données ici", height=200)
    capital = st.number_input("Capital (€)", value=500, key="cap1")
    
    if st.button("🚀 Analyser le Texte"):
        df = extraire_depuis_texte(texte_brut)
        if not df.empty:
            st.success(f"{len(df)} chevaux détectés !")
            for _, row in df.iterrows():
                prob = (1 / row['cote']) * 1.12
                val = prob * row['cote']
                if val > 1.05:
                    mise = max(0, capital * ((prob * (row['cote']-1) - (1-prob)) / (row['cote']-1)) * 0.25)
                    st.markdown(f"""<div class="card"><b>{row['nom']}</b><br>Cote: {row['cote']} | Value: {val:.2f}<br>Mise: {round(mise, 2)}€</div>""", unsafe_allow_html=True)
                    if val >= 1.10:
                        envoyer_telegram(f"💎 *VALUE*\n🐎 {row['nom']}\n📈 Cote: {row['cote']}\n💰 Mise: {round(mise, 2)}€")
        else:
            st.error("Aucune donnée détectée dans le texte.")

with tab2:
    url = st.text_input("URL de la course")
    if st.button("Analyse via URL"):
        st.warning("Zeturf bloque souvent les accès directs. Si ça échoue, utilise l'onglet 'Copier-Coller'.")
        # (Ici tu peux remettre le code de scraping précédent si tu veux tester)
