import streamlit as st
import pandas as pd
import re
import requests
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Force Alpha", layout="wide")

if "gemini" in st.secrets:
    API_KEY = st.secrets["gemini"]["api_key"]
else:
    st.error("❌ Clé API absente des Secrets.")
    st.stop()

# --- 2. FONCTIONS ---

def extraire_partants(texte):
    partants = []
    lignes = texte.strip().split('\n')
    current = None
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne: continue
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            if current: partants.append(current)
            current = {"num": str(len(partants)+1), "nom": ligne, "cote": 10.0}
        elif re.match(r'^\d+[\.,]\d+$', ligne) and current:
            try: current["cote"] = float(ligne.replace(',', '.'))
            except: pass
    if current: partants.append(current)
    return pd.DataFrame(partants)

def expertise_ultime_directe(df):
    """Teste les endpoints v1 et v1beta avec les alias de modèles les plus stables"""
    prompt = f"Expert Turf : Analyse ces partants et donne ton top 3 : {df.to_string()}"
    
    # On teste les deux versions d'API et les deux noms de modèles possibles
    configs = [
        ("v1", "gemini-1.5-flash"),
        ("v1beta", "gemini-1.5-flash"),
        ("v1", "gemini-pro"),
        ("v1beta", "gemini-pro")
    ]
    
    last_err = ""
    for version, model in configs:
        url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={API_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            if response.status_code == 200:
                res_json = response.json()
                return res_json['candidates'][0]['content']['parts'][0]['text'], f"✅ SUCCÈS ({version}/{model})"
            else:
                last_err = f"{version}/{model} -> {response.status_code}"
        except:
            continue
            
    return None, f"❌ ÉCHEC TOTAL. Google rejette votre clé sur tous les modèles. (Dernier test : {last_err})"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Connexion Forcée")

capital = st.number_input("💰 Capital (€)", value=500)
txt_in = st.text_area("📋 Collez les partants ici :", height=150)

if st.button("🚀 LANCER L'ANALYSE FINALE"):
    if txt_in:
        df = extraire_partants(txt_in)
        if not df.empty:
            with st.spinner("🔄 Tentative de connexion multi-canaux..."):
                expertise, status = expertise_ultime_directe(df)
            
            if expertise:
                st.success(status)
                st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")
            else:
                st.error(status)
                st.info("💡 Si l'échec est total : allez sur Google AI Studio, créez un NOUVEAU projet et générez une NOUVELLE clé.")

            # --- CALCULS ---
            st.write("---")
            cols = st.columns(min(len(df), 4))
            for i, row in df.iterrows():
                if i >= 4: break
                cote = max(row['cote'], 1.01)
                prob = (1 / cote) * 1.15
                kelly = (prob * (cote - 1) - (1 - prob)) / (cote - 1)
                mise = min(max(0, capital * kelly * 0.1), capital * 0.1)
                with cols[i]:
                    st.metric(label=f"n°{row['num']} - {row['nom']}", value=f"{round(mise, 2)}€")
        else:
            st.error("Aucun cheval détecté.")
