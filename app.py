import streamlit as st
import pandas as pd  # Correction ici : pandas et non pd
import re
import requests
import json
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster 2.5 : Final Pro", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; font-size: 16px !important; }
    [data-testid="stMetricLabel"] { color: #1a1a1a !important; font-weight: 700 !important; font-size: 13px !important; margin-bottom: -8px !important; }
    [data-testid="stMetric"] { background-color: #bdc3c7 !important; padding: 8px 10px !important; border-radius: 8px !important; border: 1px solid #7f8c8d !important; }
    .stButton>button { background-color: #000000; color: white; border-radius: 12px; font-weight: bold; }
    .risk-low { color: #27ae60; font-weight: bold; }
    .risk-med { color: #f39c12; font-weight: bold; }
    .risk-high { color: #e74c3c; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# st.secrets lève une exception si aucun fichier secrets.toml n'existe :
# on l'attrape pour afficher le message au lieu de planter.
try:
    API_KEY = st.secrets["gemini"]["api_key"]
except Exception:
    st.error("❌ Configurez votre API KEY dans les Secrets ([gemini] api_key = \"...\").")
    st.stop()

# --- 2. FONCTIONS DE CALCUL ---

RE_FER = re.compile(r'^(D4|DP|DA)$', re.IGNORECASE)
RE_MUSIQUE = re.compile(r'\b\d{1,2}[admphsc]\b|\b[A-Z]D\b|\bD[admp]\b')

def _est_fin_du_nom(mot):
    """Un mot qui n'appartient plus au nom : ferrure, musique, chiffre, parenthèse."""
    return bool(
        RE_FER.match(mot)
        or RE_MUSIQUE.fullmatch(mot)
        or re.match(r'^\d', mot)
        or mot.startswith('(')
        or not re.search(r'[A-Za-zÀ-ÿ]', mot)  # "---", "*", etc.
    )

def extraire_data_pro(texte):
    """Retourne (DataFrame des partants, liste des lignes non reconnues)."""
    data, ignorees = [], []
    for ligne in texte.strip().split('\n'):
        ligne = ligne.strip()
        if not ligne:
            continue
        num_match = re.match(r'^(\d{1,2})\s*[.\-):]?\s*', ligne)
        numero = num_match.group(1) if num_match else "?"
        reste = ligne[num_match.end():] if num_match else ligne

        # Le nom = tous les mots jusqu'à la ferrure / la musique (accents et noms courts acceptés)
        mots = reste.split()
        nom_mots = []
        for mot in mots:
            if _est_fin_du_nom(mot):
                break
            nom_mots.append(mot)
        nom = " ".join(nom_mots).upper()
        if not re.search(r'[A-ZÀ-Ý]', nom):  # pas de lettre = pas un nom de cheval
            ignorees.append(ligne)
            continue

        suite = " ".join(mots[len(nom_mots):])
        fer = [m for m in re.findall(r'[A-Za-z0-9]+', suite) if RE_FER.match(m)]
        musique = RE_MUSIQUE.findall(suite)
        data.append({
            "FULL_ID": f"{numero} - {nom}",
            "NUM": numero,
            "Info": f"{fer[0].upper() if fer else 'F'} | {' '.join(musique) if musique else 'N/A'}"
        })
    return pd.DataFrame(data), ignorees

def extraire_json(texte):
    """Récupère l'objet JSON même si Gemini ajoute du texte ou des ``` autour."""
    debut, fin = texte.find('{'), texte.rfind('}')
    if debut == -1 or fin == -1:
        raise ValueError("Aucun JSON dans la réponse")
    return json.loads(texte[debut:fin + 1])

def simulation_performance_max(df, hippo, discipline, capital, profil):
    partants_str = "\n".join([f"{row['FULL_ID']} ({row['Info']})" for _, row in df.iterrows()])
    
    prompt = f"""Expert Turf 2026. Hippodrome: {hippo} | Discipline: {discipline}.
    
    PARTANTS (Numéros Réels fournis) : 
    {partants_str}

    MISSION :
    1. Détermine Météo/Distance pour {hippo}.
    2. Calcule le TOP 5 Probabilités. 
    3. Analyse obligatoirement si un Outsider (🔥) a un potentiel (>5% proba) et place-le dans le podium.
    4. Génère un ticket avec UNIQUEMENT les numéros des chevaux.

    RÉPONDS EN JSON STRICT :
    {{
        "m": "☀️", "d": "2700m", "r": "Modéré", "ordre": "Num - Num - Num",
        "podium": [
            {{"n": "NUM - NOM", "p": "38%"}},
            {{"n": "NUM - NOM", "p": "22%"}},
            {{"n": "NUM - NOM", "p": "15%"}},
            {{"n": "NUM - NOM", "p": "11%"}},
            {{"n": "NUM - NOM", "p": "8%"}}
        ],
        "pari_nom": "Trio Combiné",
        "pari_nums": "12 - 4 - 7 - 1",
        "mise": "20.00", 
        "gain": "+35€"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    
    # Retourne (texte, erreur) : une des deux valeurs est None.
    # Les messages d'erreur ne reprennent jamais l'URL (elle contient la clé API).
    try:
        response = requests.post(url, json=payload, timeout=25)
    except requests.Timeout:
        return None, "Gemini n'a pas répondu à temps (25 s). Réessayez."
    except requests.RequestException:
        return None, "Impossible de joindre Gemini (problème réseau)."

    if response.status_code != 200:
        messages = {
            400: "Requête refusée par Gemini (clé API invalide ?).",
            403: "Accès refusé : vérifiez la clé API et ses droits.",
            429: "Quota Gemini dépassé. Patientez un peu avant de réessayer.",
        }
        return None, messages.get(response.status_code,
                                  f"Gemini a renvoyé une erreur (code {response.status_code}).")
    try:
        return response.json()['candidates'][0]['content']['parts'][0]['text'], None
    except (ValueError, KeyError, IndexError):
        return None, "Réponse de Gemini vide ou bloquée. Réessayez."

# --- 3. INTERFACE ---
st.title("🚀 TurfMaster 2.5 : Ultimate Investor")

with st.sidebar:
    hippo_input = st.text_input("Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot", "Plat", "Obstacles"])
    st.divider()
    capital = st.number_input("Capital (€)", value=1000)
    profil = st.select_slider("Profil de Risque", ["Prudent", "Équilibré", "Offensif"], value="Équilibré")
    if st.button("🧹 Reset"): st.rerun()

txt_in = st.text_area("📋 Collez ici (ex: 12 FAKIR D4 1a)", height=150)

if st.button("⚡ GÉNÉRER LE TICKET GAGNANT"):
    df, lignes_ignorees = extraire_data_pro(txt_in)
    if lignes_ignorees:
        st.warning("⚠️ Lignes non reconnues (ignorées) :\n\n" + "\n\n".join(f"- `{l}`" for l in lignes_ignorees))
    if not df.empty:
        with st.spinner("🧪 Analyse des cotes et détection d'outsider..."):
            raw, erreur = simulation_performance_max(df, hippo_input, discipline, capital, profil)
            if erreur:
                st.error(f"❌ {erreur}")
            if raw:
                try:
                    res = extraire_json(raw)
                    # On vérifie la réponse AVANT d'afficher quoi que ce soit
                    podium = res['podium'][:5]
                    for cle in ('r', 'd', 'm', 'ordre', 'pari_nom', 'pari_nums', 'mise', 'gain'):
                        res[cle]
                    for p in podium:
                        p['n'], p['p']
                    st.divider()
                    
                    # 1. BANDEAU INFO
                    c1, c2, c3 = st.columns([1, 1, 2])
                    color = "risk-low" if res['r'] == "Faible" else ("risk-med" if res['r'] == "Modéré" else "risk-high")
                    c1.markdown(f"Risque : <span class='{color}'>{res['r']}</span>", unsafe_allow_html=True)
                    c2.write(f"📍 {res['d']} | {res['m']}")
                    c3.info(f"🏁 Ordre : **{res['ordre']}**")

                    # 2. PODIUM (Numéro - Nom)
                    st.divider()
                    cols = st.columns(5)
                    meds = ["🥇 1er", "🥈 2ème", "🥉 3ème", "🔥 OUT", "🏇 5ème"]
                    for col, med, p in zip(cols, meds, podium):
                        col.metric(med, p['n'], p['p'])

                    # 3. TICKET FINAL (Numéros inclus)
                    st.divider()
                    l1, l2 = st.columns([2, 1])
                    with l1:
                        st.success(f"🎫 **{res['pari_nom']}** | Chevaux : **{res['pari_nums']}** | Mise : **{res['mise']} €**")
                    with l2:
                        st.metric("Gain Net Est.", res['gain'])

                except (ValueError, KeyError, TypeError):
                    st.error("Erreur d'analyse de la réponse Gemini. Réessayez l'envoi.")
    else: st.error("Veuillez saisir des partants (ex: 12 NOM).")

st.divider()
st.caption("Correction Pandas appliquée | Numéros Réels | Outsider 🔥 | Fond #bdc3c7")
