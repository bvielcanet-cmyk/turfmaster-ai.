import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import re
import requests

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .favori-box { background-color: #1e3a8a; padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 15px; border: 2px solid #fbbf24; }
    .value-card { background-color: #f0fdf4; border-left: 8px solid #22c55e; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: black; }
    .num-badge { background-color: #333; color: white; padding: 4px 12px; border-radius: 8px; font-weight: bold; font-size: 20px; margin-right: 10px; border: 2px solid #fbbf24; }
    .ticket-label { font-size: 14px; font-weight: bold; color: #475569; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS D'EXTRACTION AVANCÉES ---

def nettoyer_nom(nom):
    """Nettoie le nom du cheval des résidus de caractères gras ou spéciaux."""
    if not nom: return "Inconnu"
    # Supprime tout ce qui n'est pas lettre, chiffre ou espace
    nom = re.sub(r'[^a-zA-ZÀ-ÿ0-9\s]', '', nom)
    # Supprime les chiffres isolés (souvent des numéros de dossard restants)
    nom = re.sub(r'\b\count\b', '', nom)
    return nom.strip().upper()

def extraire_depuis_texte(texte):
    partants = []
    # On sépare par lignes et on nettoie les espaces vides
    lignes = [l.strip() for l in texte.split('\n') if l.strip()]
    
    for i, ligne in enumerate(lignes):
        # 1. Recherche de la cote (format 4.5 ou 4,5 ou 12)
        cote_match = re.search(r"\b(\d+[,\.]\d+|\d{1,3})\b$", ligne)
        
        if cote_match:
            try:
                cote = float(cote_match.group(1).replace(',', '.'))
                if cote <= 1.0: continue
                
                # 2. Recherche du numéro (souvent au début de la ligne ou juste avant la cote)
                # On cherche un nombre de 1 à 2 chiffres au début de la ligne actuelle ou précédente
                num_match = re.search(r"^(\d{1,2})\b", ligne)
                if not num_match and i > 0:
                    num_match = re.search(r"^(\d{1,2})\b", lignes[i-1])
                
                numero = num_match.group(1) if num_match else "?"
                
                # 3. Recherche du nom (Souvent entre le numéro et la cote)
                nom_brut = ligne
                if numero != "?": nom_brut = nom_brut.replace(numero, "", 1)
                nom_brut = nom_brut.replace(cote_match.group(1), "").strip()
                
                # Si la ligne est vide après retrait, le nom était sans doute à la ligne d'avant
                if len(nom_brut) < 2 and i > 0:
                    nom_brut = lignes[i-1]
                    if numero != "?": nom_brut = nom_brut.replace(numero, "", 1)
                
                nom_final = nettoyer_nom(nom_brut)
                if nom_final:
                    partants.append({"num": numero, "nom": nom_final, "cote": cote})
            except: continue
            
    return pd.DataFrame(partants).drop_duplicates(subset=['nom'])

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI Pro v3.5")
st.info(f"🕒 Analyse du {datetime.now(tz_paris).strftime('%d/%m/%Y à %H:%M')}")

st.markdown("### 📋 Importation des données")
texte_brut = st.text_area("Copier/Coller Zeturf (inclure numéros, noms et cotes) :", height=180)
capital = st.number_input("💰 Capital disponible (€)", value=500, min_value=10)

if st.button("⚡ ANALYSER ET GÉNÉRER LES MISES"):
    if not texte_brut:
        st.warning("Veuillez coller les données de la course.")
    else:
        df = extraire_depuis_texte(texte_brut)
        if not df.empty:
            # Algorithme Kelly + Marge IA
            resultats = []
            for _, row in df.iterrows():
                prob = (1 / row['cote']) * 1.15
                v = prob * row['cote']
                m = max(0, capital * ((prob * (row['cote']-1) - (1-prob)) / (row['cote']-1)) * 0.20)
                resultats.append({"num": row['num'], "nom": row['nom'], "cote": row['cote'], "value": v, "m": m, "prob": prob * 100})

            ordre = sorted(resultats, key=lambda x: x['prob'], reverse=True)
            
            # --- TICKET RAPIDE ---
            st.markdown("<p class='ticket-label'>🎫 TICKET À COPIER (TOP 5)</p>", unsafe_allow_html=True)
            top_nums = " - ".join([r['num'] for r in ordre[:5]])
            st.code(top_nums, language="text")

            # --- AFFICHAGE STRATÉGIQUE ---
            # Favori
            f = ordre[0]
            st.markdown(f"""
                <div class="favori-box">
                    <h3 style="margin:0; color:white;">🏆 PREMIER DU CLASSEMENT</h3>
                    <h1 style="margin:10px 0; color:#fbbf24;"><span style="color:white; font-size:30px;">#{f['num']}</span> {f['nom']}</h1>
                    <p style="margin:0; font-size:18px;">Indice de confiance : <b>{f['prob']:.1f}%</b></p>
                </div>
            """, unsafe_allow_html=True)

            # Mises
            st.subheader("💰 Mises conseillées")
            vals = [r for r in resultats if r['value'] > 1.05]
            if vals:
                for v in sorted(vals, key=lambda x: x['value'], reverse=True):
                    st.markdown(f"""
                        <div class="value-card">
                            <span class="num-badge">{v['num']}</span> <b style="font-size:18px;">{v['nom']}</b>
                            <br>📈 Cote : {v['cote']} | Value : {v['value']:.2f}
                            <br><span style="font-size:20px; color:#166534;">👉 Miser : <b>{v['m']:.2f}€</b></span>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Aucun cheval ne présente un avantage mathématique suffisant.")

            # Coup de Poker
            poker = [r for r in resultats if r['cote'] >= 12 and r['prob'] > 4]
            if poker:
                cp = max(poker, key=lambda x: x['value'])
                st.markdown(f"""
                    <div class="poker-card">
                        <h4 style="margin:0; color:#ea580c;">🃏 COUP DE POKER</h4>
                        <span class="num-badge">{cp['num']}</span> <b>{cp['nom']}</b> (Cote : {cp['cote']})
                    </div>
                """, unsafe_allow_html=True)

            # Podium
            with st.expander("📊 Arrivée estimée (Top 6)"):
                for i, r in enumerate(ordre[:6]):
                    st.write(f"{i+1}. **N°{r['num']}** {r['nom']} ({r['prob']:.1f}%)")

            # Envoi Telegram
            msg = f"🏇 *ANALYSE TERMINÉE*\n🎫 Ticket : `{top_nums}`\n🏆 Favori : N°{f['num']} {f['nom']}\n💰 Value : {vals[0]['nom'] if vals else 'Néant'}"
            url_tg = f"https://api.telegram.org/bot{DIRECT_TOKEN}/sendMessage"
            requests.post(url_tg, data={"chat_id": DIRECT_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
            
        else:
            st.error("❌ Échec de l'analyse. Vérifie que tu as bien copié les colonnes Numéros, Noms et Cotes.")
