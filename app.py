import streamlit as st
import pandas as pd
import re
import requests
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI : Ultra-Performance", layout="wide")

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
            current = {"num": str(len(partants)+1), "nom": ligne, "cote": 10.0, "musique": "Inconnue"}
        elif re.match(r'^\d+[\.,]\d+$', ligne) and current:
            try: current["cote"] = float(ligne.replace(',', '.'))
            except: pass
        elif re.search(r'\d+[apmsh]', ligne.lower()) and current:
            current["musique"] = ligne
    if current: partants.append(current)
    return pd.DataFrame(partants)

def expertise_http_direct(df):
    """Envoi direct au serveur Google (Contourne tous les bugs de SDK)"""
    prompt = f"Expert Turf : Analyse ces partants et donne ton top 3 : {df.to_string()}"
    
    # On tente le modèle 1.5-flash qui est le plus universel en HTTP
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        res_json = response.json()
        
        if response.status_code == 200:
            text_output = res_json['candidates'][0]['content']['parts'][0]['text']
            return text_output, "✅ CONNEXION DIRECTE RÉUSSIE (HTTP v1)"
        else:
            return None, f"❌ Erreur Serveur {response.status_code}: {res_json.get('error', {}).get('message', 'Inconnue')}"
    except Exception as e:
        return None, f"❌ Erreur Réseau : {str(e)}"

# --- 3. INTERFACE ---

st.title("🏇 TurfMaster AI : Mode Direct 2026")

capital = st.number_input("💰 Votre Capital (€)", value=500)
txt_in = st.text_area("📋 Collez les partants ici :", height=150)

if st.button("🔍 ANALYSER LA COURSE"):
    if txt_in:
        df = extraire_partants(txt_in)
        if not df.empty:
            with st.spinner("🚀 Communication directe avec Google Gemini..."):
                expertise, status = expertise_http_direct(df)
            
            if expertise:
                st.success(status)
                st.markdown(f"### 🎯 Verdict de l'IA\n{expertise}")
            else:
                st.error(status)
                st.warning("Mode Statistique activé.")

            # --- CALCULS DE MISE ---
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
                    st.caption(f"Cote: {cote}")
        else:
            st.error("Aucun cheval détecté.")
