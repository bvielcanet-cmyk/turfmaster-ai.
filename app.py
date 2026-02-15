import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import re
import requests

# --- 1. CONFIGURATION & DESIGN ---
st.set_page_config(page_title="TurfMaster AI Pro v4", page_icon="🏇", layout="centered")
tz_paris = pytz.timezone('Europe/Paris')

DIRECT_TOKEN = "8547396162:AAHgpnvmfwJ1jNgEu-T7kfdVCT-NKWvo5P4"
DIRECT_CHAT_ID = "8336554838"

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; }
    .favori-box { background-color: #1e3a8a; padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 15px; border: 2px solid #fbbf24; }
    .value-card { background-color: #f0fdf4; border-left: 8px solid #22c55e; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: black; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .poker-card { background-color: #fff7ed; border: 2px dashed #f97316; padding: 15px; border-radius: 10px; margin-top: 10px; color: black; }
    .num-badge { background-color: #333; color: white; padding: 4px 12px; border-radius: 8px; font-weight: bold; font-size: 20px; margin-right: 10px; border: 2px solid #fbbf24; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS DE SECOURS ---

def envoyer_telegram(message):
    url_tg = f"https://api.telegram.org/bot{DIRECT_TOKEN}/sendMessage"
    try:
        requests.post(url_tg, data={"chat_id": DIRECT_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def extraire_depuis_texte(texte):
    """Méthode de scan global : Numéro -> Nom (MAJ) -> Cote"""
    partants = []
    # Nettoyage simple
    texte = texte.replace('\r', '\n')
    
    # On cherche les numéros de 1 à 22
    for n in range(1, 23):
        n_str = str(n)
        # Trouve le numéro entouré d'espaces ou en début de ligne
        regex_num = rf"(?:^|\s){n_str}(?:\s|$|\.)"
        match = re.search(regex_num, texte)
        
        if match:
            start_pos = match.end()
            # On analyse les 120 caractères suivants
            fenetre = texte[start_pos:start_pos + 120]
            
            # 1. On cherche la cote (ex: 4.5 ou 12)
            cotes = re.findall(r"\b\d+[,\.]\d+\b|\b\d{1,2}\b", fenetre)
            
            # 2. On cherche le nom (Mots en MAJUSCULES de 3 lettres ou plus)
            noms = re.findall(r"\b[A-ZÀ-Ÿ]{3,}\b", fenetre)
            
            if cotes and noms:
                # Le premier nom trouvé est souvent le bon
                nom_final = " ".join(noms[:2]) 
                # On cherche la première cote qui n'est pas le numéro lui-même
                try:
                    for c in cotes:
                        c_val = float(c.replace(',', '.'))
                        if c_val > 1.1 and c_val != float(n):
                            partants.append({
                                "num": n_str,
                                "nom": nom_final,
                                "cote": c_val
                            })
                            break
                except: continue
    
    # Fallback si rien trouvé : recherche ligne par ligne structurée
    if not partants:
        for ligne in texte.split('\n'):
            m = re.search(r"(\d{1,2})\s+([A-ZÀ-Ÿ\s]{3,})\s+(\d+[,\.]\d+|\d+)", ligne)
            if m:
                partants.append({"num": m.group(1), "nom": m.group(2).strip(), "cote": float(m.group(3).replace(',', '.'))})
                
    return pd.DataFrame(partants).drop_duplicates(subset=['num'])

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI Pro")
st.info(f"🕒 Analyse du {datetime.now(tz_paris).strftime('%H:%M:%S')}")

texte_brut = st.text_area("Colle ici tout le texte de la page Zeturf :", height=200, placeholder="Sélectionne tout sur Zeturf et colle ici...")
capital = st.number_input("💰 Ton Capital (€)", value=500, min_value=10)

if st.button("🚀 LANCER L'ANALYSE"):
    if not texte_brut:
        st.warning("La zone de texte est vide.")
    else:
        with st.spinner("Analyse en cours..."):
            df = extraire_depuis_texte(texte_brut)
            
            if not df.empty:
                resultats = []
                for _, row in df.iterrows():
                    prob = (1 / row['cote']) * 1.15
                    val = prob * row['cote']
                    mise = max(0, capital * ((prob * (row['cote']-1) - (1-prob)) / (row['cote']-1)) * 0.20)
                    resultats.append({
                        "num": row['num'], "nom": row['nom'], "cote": row['cote'], "value": val, "mise": mise, "prob": prob * 100
                    })

                ordre = sorted(resultats, key=lambda x: x['prob'], reverse=True)
                
                # --- TICKET RAPIDE ---
                st.subheader("🎫 Ticket à copier (Top 5)")
                ticket = " - ".join([r['num'] for r in ordre[:5]])
                st.code(ticket, language="text")

                # --- FAVORI IA ---
                f = ordre[0]
                st.markdown(f"""
                    <div class="favori-box">
                        <h3 style="margin:0; color:white;">🏆 FAVORI IA</h3>
                        <h1 style="margin:10px 0; color:#fbbf24;"><span style="color:white;">#{f['num']}</span> {f['nom']}</h1>
                        <p style="margin:0; font-size:18px;">Confiance : <b>{f['prob']:.1f}%</b></p>
                    </div>
                """, unsafe_allow_html=True)

                # --- VALUETRADER ---
                st.subheader("💰 Mises conseillées")
                values = [r for r in resultats if r['value'] > 1.05]
                if values:
                    for v in sorted(values, key=lambda x: x['value'], reverse=True):
                        st.markdown(f"""
                            <div class="value-card">
                                <span class="num-badge">{v['num']}</span> <b style="font-size:18px;">{v['nom']}</b><br>
                                <span style="font-size:19px; color:#166534;">Miser : <b>{v['mise']:.2f}€</b></span> (Cote: {v['cote']})
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Aucune value détectée.")

                # --- COUP DE POKER ---
                poker = [r for r in resultats if r['cote'] >= 12 and r['prob'] > 4]
                if poker:
                    cp = max(poker, key=lambda x: x['value'])
                    st.markdown(f"""
                        <div class="poker-card">
                            <h4 style="margin:0; color:#ea580c;">🃏 COUP DE POKER</h4>
                            <span class="num-badge">{cp['num']}</span> <b>{cp['nom']}</b> (Cote : {cp['cote']})
                        </div>
                    """, unsafe_allow_html=True)

                # --- TELEGRAM ---
                msg = f"🏇 *TURFMASTER*\n🎫 Ticket: `{ticket}`\n🏆 Favori: #{f['num']} {f['nom']}"
                envoyer_telegram(msg)
                
            else:
                st.error("❌ Échec de l'analyse. Vérifie que tu as bien copié les cotes et les noms.")
                st.info("Astuce : Sur Zeturf mobile, essaie de copier du numéro 1 jusqu'à la dernière cote du tableau.")

# --- 4. HISTORIQUE RAPIDE ---
with st.expander("📈 Suivi Bankroll"):
    if 'total_gain' not in st.session_state: st.session_state.total_gain = 0.0
    with st.form("gain_form"):
        g = st.number_input("Gain ou Perte de la course (€)", value=0.0)
        if st.form_submit_button("Enregistrer"):
            st.session_state.total_gain += g
    st.metric("Profit Total", f"{st.session_state.total_gain:.2f} €")
