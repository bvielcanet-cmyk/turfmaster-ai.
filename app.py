import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# --- 1. CONFIGURATION ET DESIGN ---
st.set_page_config(page_title="TurfMaster AI Pro", page_icon="🏇", layout="centered")

# Fuseau horaire de Paris
tz_paris = pytz.timezone('Europe/Paris')

# Design mobile
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #28a745; color: white; font-weight: bold; font-size: 18px; }
    .card { background-color: white; border-radius: 15px; padding: 20px; border: 1px solid #eee; margin-bottom: 15px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05); }
    .badge { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; color: white; float: right; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS LOGIQUES ---

def temps_restant(heure_course):
    try:
        maintenant = datetime.now(tz_paris)
        heure_str = heure_course.lower().replace('h', ':').strip()
        h, m = map(int, heure_str.split(':'))
        depart = maintenant.replace(hour=h, minute=m, second=0, microsecond=0)
        diff = depart - maintenant
        return int(diff.total_seconds() / 60)
    except: return None

def extraire_donnees(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        header = soup.find('div', class_='course-header-info')
        info_temps = header.text.strip() if header else "Aujourd'hui - 00h00"
        heure_c = info_temps.split('-')[1].strip() if '-' in info_temps else "00h00"

        partants = []
        for ligne in soup.select('tr.runner-row'):
            nom = ligne.find('span', class_='runner-name').text.strip()
            cote_raw = ligne.find('span', class_='cote-live').text.strip().replace(',', '.')
            if cote_raw:
                partants.append({"nom": nom, "cote": float(cote_raw), "heure": heure_c})
        return pd.DataFrame(partants)
    except: return pd.DataFrame()

def calculer_kelly(cote, capital, avantage=1.12, fraction=0.25):
    prob_reelle = (1 / cote) * avantage
    if prob_reelle * cote <= 1: return 0, prob_reelle
    kelly = (prob_reelle * (cote - 1) - (1 - prob_reelle)) / (cote - 1)
    return max(0, capital * kelly * fraction), prob_reelle

def envoyer_telegram(message):
    token = st.secrets.get("TELEGRAM_TOKEN")
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        url_tg = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url_tg, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
            return True
        except: return False
    return False

# --- 3. INTERFACE UTILISATEUR ---

st.title("🏇 TurfMaster AI Pro")
heure_actuelle = datetime.now(tz_paris).strftime("%H:%M:%S")
st.info(f"🕒 Heure de Paris : **{heure_actuelle}**")

# Bouton de Test Telegram
if st.button("🔔 Tester la connexion Telegram"):
    if envoyer_telegram("✅ Test de connexion réussi depuis TurfMaster !"):
        st.success("Message envoyé ! Vérifie ton Telegram.")
    else:
        st.error("Échec de l'envoi. Vérifie tes Secrets (Token et Chat ID).")

st.divider()

# Analyse Multi-liens
st.subheader("🚀 Analyse Globale de la Journée")
urls_input = st.text_area("Colle les URLs Zeturf (une par ligne) :", height=150)
capital = st.number_input("💰 Capital total (€)", value=500, min_value=10)

if st.button("⚡ LANCER L'ANALYSE ET LES ALERTES"):
    if urls_input:
        urls = urls_input.strip().split('\n')
        for url in urls:
            url = url.strip()
            if not url: continue
            
            df = extraire_donnees(url)
            if not df.empty:
                nom_c = url.split('/')[-2].replace('-', ' ').title()
                st.markdown(f"#### 🏁 {nom_c}")
                
                for _, row in df.iterrows():
                    mise, prob = calculer_kelly(row['cote'], capital)
                    val = prob * row['cote']
                    mins = temps_restant(row['heure'])
                    
                    if mins is None: b_col, b_txt = "#666", "?"
                    elif mins <= 0: b_col, b_txt = "#000", "Parti"
                    elif mins < 15: b_col, b_txt = "#d9534f", f"{mins} min"
                    else: b_col, b_txt = "#5cb85c", f"{mins} min"

                    if val > 1.05:
                        st.markdown(f"""
                        <div class="card">
                            <span class="badge" style="background-color: {b_col};">{b_txt}</span>
                            <b>{row['nom']}</b> | Cote: {row['cote']} | Value: {val:.2f}<br>
                            <span style="color: #28a745; font-weight: bold;">Mise Kelly : {mise:.2f}€</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Envoi automatique si grosse Value
                        if val >= 1.10:
                            envoyer_telegram(f"🏇 *VALUE DETECTÉE*\nCourse: {nom_c}\n🐎 {row['nom']}\n📈 Cote: {row['cote']}\n💰 Mise: {round(mise, 2)}€")
    else:
        st.warning("Veuillez entrer au moins un lien.")

# --- 4. BILAN ---
st.divider()
if 'log' not in st.session_state: st.session_state.log = []

with st.expander("📝 Enregistrer un résultat"):
    with st.form("pari_form"):
        f_nom = st.text_input("Nom du cheval")
        f_mise = st.number_input("Mise (€)", value=10.0)
        f_cote = st.number_input("Cote réelle", value=2.0)
        f_res = st.radio("Résultat", ["Gagné ✅", "Perdu ❌"], horizontal=True)
        if st.form_submit_button("Sauvegarder"):
            gain = (f_mise * f_cote - f_mise) if "Gagné" in f_res else -f_mise
            st.session_state.log.append({"nom": f_nom, "gain": gain, "date": datetime.now(tz_paris).strftime("%H:%M")})
            st.success("Enregistré !")

if st.session_state.log:
    df_res = pd.DataFrame(st.session_state.log)
    st.metric("Profit Total", f"{df_res['gain'].sum():+.2f} €")
    st.dataframe(df_res, use_container_width=True)
