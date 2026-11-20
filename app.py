from datetime import datetime

import pandas as pd
import streamlit as st

import turf_logic as tl

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

FEUILLE = "TurfMaster"  # onglet du Google Sheet où sont rangés les tickets


# --- 2. SERVICES ---

@st.cache_data(ttl=3600, show_spinner=False)
def analyser_course(partants_str, hippo, discipline, profil, recherche, _api_key):
    """Appel Gemini mis en cache 1 h : recoller la même course ne consomme pas de quota.
    Les erreurs (exceptions) ne sont jamais mises en cache."""
    prompt = tl.construire_prompt(partants_str, hippo, discipline, profil, recherche)
    return tl.appeler_gemini(_api_key, prompt, recherche)


def connexion_sheets():
    """Retourne (connexion, message). La connexion est None si l'historique est indisponible."""
    try:
        cfg = st.secrets.get("connections", {}).get("gsheets")
    except Exception:
        cfg = None
    if not cfg:
        return None, ("Historique désactivé : ajoutez une section `[connections.gsheets]` "
                      "dans les Secrets (voir le README).")
    if cfg.get("type") != "service_account":
        return None, ("Historique en lecture seule impossible à mettre à jour : "
                      "il faut un compte de service Google (voir le README).")
    try:
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection), None
    except Exception:
        return None, "Connexion au Google Sheet impossible. Vérifiez les Secrets."


def lire_historique(conn):
    """Retourne (DataFrame, onglet_existe)."""
    try:
        df = conn.read(worksheet=FEUILLE, ttl=0)
    except Exception:
        return pd.DataFrame(columns=tl.COLONNES_HISTORIQUE), False
    df = df.dropna(how="all")
    for col in tl.COLONNES_HISTORIQUE:
        if col not in df.columns:
            df[col] = None
    return df[tl.COLONNES_HISTORIQUE], True


def ecrire_historique(conn, df, existe):
    if existe:
        conn.update(worksheet=FEUILLE, data=df)
    else:
        conn.create(worksheet=FEUILLE, data=df)


# --- 3. INTERFACE ---
st.title("🚀 TurfMaster 2.5 : Ultimate Investor")

with st.sidebar:
    hippo_input = st.text_input("Hippodrome", value="Vincennes")
    discipline = st.selectbox("Discipline", ["Trot", "Plat", "Obstacles"])
    st.divider()
    capital = st.number_input("Capital (€)", value=1000, min_value=0)
    profil = st.select_slider("Profil de Risque", ["Prudent", "Équilibré", "Offensif"], value="Équilibré")
    st.caption(f"Mise conseillée : {tl.POURCENTAGE_MISE[profil]:.0%} du capital "
               f"= **{tl.calculer_mise(capital, profil):.2f} €**")
    recherche = st.toggle("🔎 Recherche Google (météo, terrain, cotes)", value=True,
                          help="Gemini cherche les infos du jour sur internet. "
                               "Si l'option n'est pas disponible, l'analyse se fait sans.")
    if st.button("🧹 Reset"):
        st.session_state.pop("resultat", None)
        st.rerun()

conn, message_sheets = connexion_sheets()
onglet_prono, onglet_histo = st.tabs(["🎯 Pronostic", "📊 Historique"])

with onglet_prono:
    txt_in = st.text_area("📋 Collez ici (ex: 12 FAKIR D4 1a 2a 4.5 — la cote est facultative)", height=150)

    if st.button("⚡ GÉNÉRER LE TICKET GAGNANT"):
        st.session_state.pop("resultat", None)
        df, lignes_ignorees = tl.extraire_data_pro(txt_in)
        if lignes_ignorees:
            st.warning("⚠️ Lignes non reconnues (ignorées) :\n\n"
                       + "\n\n".join(f"- `{l}`" for l in lignes_ignorees))
        if df.empty:
            st.error("Veuillez saisir des partants (ex: 12 NOM).")
        else:
            partants_str = "\n".join(f"{row['FULL_ID']} ({row['Info']})" for _, row in df.iterrows())
            with st.spinner("🧪 Analyse des cotes et détection d'outsider..."):
                try:
                    raw, recherche_utilisee = analyser_course(
                        partants_str, hippo_input, discipline, profil, recherche, API_KEY)
                    res = tl.valider_reponse(tl.extraire_json(raw))
                    st.session_state["resultat"] = {
                        "res": res, "mise": tl.calculer_mise(capital, profil),
                        "hippo": hippo_input, "discipline": discipline, "profil": profil,
                        "recherche_demandee": recherche, "recherche_utilisee": recherche_utilisee,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "enregistre": False,
                    }
                except tl.GeminiErreur as e:
                    st.error(f"❌ {e}")
                except (ValueError, KeyError, TypeError):
                    st.error("Erreur d'analyse de la réponse Gemini. Réessayez l'envoi.")

    # Le résultat est gardé en mémoire : il reste affiché quand on clique sur « Enregistrer ».
    r = st.session_state.get("resultat")
    if r:
        res = r["res"]
        st.divider()
        if r["recherche_demandee"] and not r["recherche_utilisee"]:
            st.info("ℹ️ Recherche Google indisponible : analyse faite sans données du jour.")

        # 1. BANDEAU INFO
        c1, c2, c3 = st.columns([1, 1, 2])
        color = ("risk-low" if res['r'] == "Faible"
                 else "risk-med" if res['r'] == "Modéré" else "risk-high")
        c1.markdown(f"Risque : <span class='{color}'>{res['r']}</span>", unsafe_allow_html=True)
        c2.write(f"📍 {res['d']} | {res['m']}")
        c3.info(f"🏁 Ordre : **{res['ordre']}**")

        # 2. PODIUM (Numéro - Nom), l'outsider signalé par Gemini porte 🔥
        st.divider()
        cols = st.columns(5)
        meds = ["🥇 1er", "🥈 2ème", "🥉 3ème", "🏇 4ème", "🏇 5ème"]
        for col, med, p in zip(cols, meds, res['podium']):
            col.metric(f"{med} 🔥 OUT" if p['out'] else med, p['n'], p['p'])

        # 3. TICKET FINAL
        st.divider()
        l1, l2 = st.columns([2, 1])
        with l1:
            st.success(f"🎫 **{res['pari_nom']}** | Chevaux : **{res['pari_nums']}** "
                       f"| Mise : **{r['mise']:.2f} €** ({r['profil']})")
        with l2:
            st.metric("Gain net estimé (pour 1 €, IA)", res['gain'])
        st.caption("Les probabilités sont des estimations de l'IA, pas une garantie. "
                   "Suivez vos résultats dans l'onglet Historique.")

        if conn is not None:
            if r["enregistre"]:
                st.success("✅ Ticket enregistré dans l'historique.")
            elif st.button("💾 Enregistrer le ticket"):
                try:
                    histo, existe = lire_historique(conn)
                    ligne = tl.ligne_historique(r["date"], r["hippo"], r["discipline"],
                                                r["profil"], res, r["mise"])
                    ecrire_historique(conn, pd.concat([histo, pd.DataFrame([ligne])],
                                                      ignore_index=True), existe)
                    r["enregistre"] = True
                    st.rerun()
                except Exception:
                    st.error("Impossible d'écrire dans le Google Sheet. "
                             "Vérifiez qu'il est partagé avec le compte de service.")

with onglet_histo:
    if conn is None:
        st.info(message_sheets)
    else:
        histo, existe = lire_historique(conn)
        stats = tl.calculer_stats(histo)
        m = st.columns(5)
        m[0].metric("Tickets", f"{stats['nb_tickets']} ({stats['nb_resolus']} joués)")
        m[1].metric("Réussite", f"{stats['reussite']:.0f} %")
        m[2].metric("Misé", f"{stats['mise_totale']:.2f} €")
        m[3].metric("Bénéfice", f"{stats['benefice']:+.2f} €")
        m[4].metric("ROI", f"{stats['roi']:+.1f} %")

        if histo.empty:
            st.caption("Aucun ticket enregistré pour l'instant.")
        else:
            st.caption("Après la course, choisissez Gagné ou Perdu et indiquez la somme rapportée, "
                       "puis enregistrez.")
            histo["resultat"] = histo["resultat"].where(histo["resultat"].isin(tl.RESULTATS), "En attente")
            histo["gain_reel"] = pd.to_numeric(histo["gain_reel"], errors="coerce").fillna(0.0)
            modifie = st.data_editor(
                histo, hide_index=True, width="stretch",
                disabled=[c for c in tl.COLONNES_HISTORIQUE if c not in ("resultat", "gain_reel")],
                column_config={
                    "resultat": st.column_config.SelectboxColumn("Résultat", options=tl.RESULTATS),
                    "gain_reel": st.column_config.NumberColumn("Rapporté (€)", min_value=0.0, format="%.2f"),
                    "mise": st.column_config.NumberColumn("Mise (€)", format="%.2f"),
                },
            )
            if st.button("💾 Enregistrer les résultats"):
                try:
                    ecrire_historique(conn, modifie, existe)
                    st.success("✅ Résultats enregistrés.")
                except Exception:
                    st.error("Impossible d'écrire dans le Google Sheet.")

st.divider()
st.caption("Mise calculée selon le profil | Recherche Google | Outsider 🔥 | Historique Google Sheets")
