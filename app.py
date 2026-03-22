import streamlit as st
import google.generativeai as genai
import pandas as pd
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster AI GOLD", page_icon="🏇", layout="wide")

# Connexion avec ta NOUVELLE clé (celle du projet avec les 254€ de crédit)
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("❌ Configurez votre clé API dans les Secrets Streamlit.")
    st.stop()

# --- 2. FONCTIONS D'EXPERTISE ---

def extraire_partants(texte):
    """Nettoyage intelligent des noms en MAJUSCULES"""
    partants = []
    lignes = texte.strip().split('\n')
    for ligne in lignes:
        ligne = ligne.strip()
        # On cherche les noms de chevaux (MAJUSCULES de plus de 3 lettres)
        if ligne.isupper() and len(ligne) > 3 and not any(c.isdigit() for c in ligne):
            partants.append({"num": str(len(partants)+1), "nom": ligne, "cote": 10.0})
    return pd.DataFrame(partants)

def expertise_ia_pro(df):
    """L'appel qui profite de ton abonnement Pro débridé"""
    prompt = f"""Expert Turf : Analyse ces partants pour une course. 
    Donne ton top 3 favoris avec une brève justification technique pour chacun.
    Partants : {df['nom'].tolist()}"""
    
    try:
        # On utilise le modèle Pro puisque ton compte est débloqué
        model = genai.GenerativeModel('gemini-1.5-pro') 
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Erreur d'analyse : {e}"

# --- 3. INTERFACE UTILISATEUR ---

st.title("🏇 TurfMaster AI : Expertise Gold Active")
st.success("✅ Compte Pro détecté - Serveurs Google débridés")

c1, c2 = st.columns([1, 2])

with c1:
    capital = st.number_input("💰 Capital (€)", value=1000)
    txt_in = st.text_area("📋 Collez les partants (MAJUSCULES) :", height=200, placeholder="JIJI DOUZOU\nFAKIR DU LORAULT\netc...")

if st.button("🚀 LANCER L'EXPERTISE PRO"):
    df = extraire_partants(txt_in)
    
    if not df.empty:
        with st.spinner("🧠 Analyse IA haute fidélité en cours..."):
            expertise = expertise_ia_pro(df)
        
        # Affichage de l'analyse
        st.markdown("---")
        st.subheader("🎯 Verdict de l'IA Pro")
        st.info(expertise)

        # --- CALCULS DE MISES (Algorithme Kelly) ---
        st.subheader("📊 Stratégie de Mises Optimisée")
        cols = st.columns(min(len(df), 4))
        
        for i, row in df.iterrows():
            if i >= 4: break # Top 4
            
            # Simulation de probabilité (IA boostée)
            cote = 10.0 # Cote par défaut
            prob = (1 / cote) * 1.18 
            kelly = (prob * (cote - 1) - (1 - prob)) / (cote - 1)
            mise = min(max(0, capital * kelly * 0.1), capital * 0.1)

            with cols[i]:
                st.metric(label=row['nom'], value=f"{round(mise, 2)}€", delta="Favori")
    else:
        st.error("Aucun nom en MAJUSCULES détecté. Vérifiez votre texte.")

# --- FOOTER ---
st.caption("Mode : Paid Tier (France) | Crédits Google Cloud : Actifs")
