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
AUTO = "Auto (d'après la musique)"


# --- 2. SERVICES ---

@st.cache_data(ttl=6 * 3600, show_spinner=False)
def contexte_du_jour(hippo, discipline, jour, _api_key):
    """Recherche Google faite une fois par hippodrome et par jour (6 h de cache)."""
    return tl.rechercher_contexte(_api_key, hippo, discipline, jour)


@st.cache_data(ttl=3600, show_spinner=False)
def analyser_course(partants_str, hippo, discipline, profil, contexte, _api_key):
    """Analyse mise en cache 1 h : recoller la même course ne consomme pas de quota.
    Les erreurs (exceptions) ne sont jamais mises en cache."""
    return tl.analyser(_api_key, tl.construire_prompt(partants_str, hippo, discipline, profil, contexte))


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
        return None, ("Historique impossible à mettre à jour : "
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


def pct(x):
    return "—" if x is None or pd.isna(x) else f"{x:.0%}"


# --- 3. INTERFACE ---
st.title("🚀 TurfMaster 2.5 : Ultimate Investor")

with st.sidebar:
    hippo_input = st.text_input("Hippodrome", value="Vincennes")
    choix_discipline = st.selectbox("Discipline", [AUTO] + tl.DISCIPLINES)
    st.divider()
    capital = st.number_input("Capital (€)", value=1000, min_value=0)
    profil = st.select_slider("Profil de Risque", list(tl.PROFILS), value="Équilibré")
    st.caption(f"Pari conseillé seulement si : {tl.decrire_profil(profil)}.")
    limite_pertes = st.number_input("Perte max sur 7 jours (€, 0 = sans limite)", value=100, min_value=0,
                                    help="Vérifiée avec l'historique Google Sheets.")
    recherche = st.toggle("🔎 Recherche Google (météo, terrain, distance)", value=True,
                          help="Faite une fois par hippodrome et par jour, puis réutilisée.")
    if st.button("🧹 Reset"):
        st.session_state.pop("resultat", None)
        st.rerun()

conn, message_sheets = connexion_sheets()
onglet_prono, onglet_histo = st.tabs(["🎯 Pronostic", "📊 Historique"])

with onglet_prono:
    txt_in = st.text_area("📋 Collez les partants copiés depuis le site (avec les cotes), ou un cheval par ligne "
                          "(ex: 12 FAKIR D4 1a 2a 4.5)", height=200)

    if st.button("⚡ ANALYSER LA COURSE"):
        st.session_state.pop("resultat", None)
        df, lignes_ignorees = tl.extraire_data_pro(txt_in)
        if lignes_ignorees:
            st.warning("⚠️ Lignes non reconnues (ignorées) :\n\n"
                       + "\n\n".join(f"- `{l}`" for l in lignes_ignorees))
        if df.empty:
            st.error("Veuillez saisir des partants (ex: 12 NOM).")
        else:
            notes = []
            detectee = tl.detecter_discipline(df)
            if choix_discipline == AUTO:
                discipline = detectee or "Non précisée"
            else:
                discipline = choix_discipline
                if detectee and detectee != discipline:
                    notes.append(f"La musique des chevaux indique plutôt **{detectee}** "
                                 f"alors que vous avez choisi **{discipline}**.")
            partants_str = "\n".join(f"{row['FULL_ID']} ({row['Info']})" for _, row in df.iterrows())

            with st.spinner("🧪 Analyse de la course et calcul de la valeur..."):
                try:
                    contexte = None
                    if recherche:
                        try:
                            contexte = contexte_du_jour(hippo_input, discipline,
                                                        datetime.now().strftime("%d/%m/%Y"), API_KEY)
                        except tl.GeminiErreur as e:
                            notes.append(f"Recherche Google indisponible ({e}) : analyse sans données du jour.")
                    raw = analyser_course(partants_str, hippo_input, discipline, profil, contexte, API_KEY)
                    res, alertes = tl.valider_reponse(tl.extraire_json(raw), df)

                    budget = None
                    if limite_pertes > 0:
                        if conn is not None:
                            histo, _ = lire_historique(conn)
                            perte = tl.pertes_recentes(histo, pd.Timestamp.now())
                            budget = limite_pertes - max(perte, 0)
                        else:
                            notes.append("Limite de pertes non vérifiée : l'historique Google Sheets n'est pas configuré.")
                    decision = tl.evaluer_pari(res["chevaux"], df, capital, profil, budget)

                    st.session_state["resultat"] = {
                        "res": res, "decision": decision, "alertes": alertes, "notes": notes,
                        "hippo": hippo_input, "discipline": discipline, "profil": profil,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "enregistre": False,
                    }
                except tl.GeminiErreur as e:
                    st.error(f"❌ {e}")
                except (ValueError, KeyError, TypeError):
                    st.error("Erreur d'analyse de la réponse Gemini. Réessayez l'envoi.")

    # Le résultat est gardé en mémoire : il reste affiché quand on clique sur « Enregistrer ».
    r = st.session_state.get("resultat")
    if r:
        res, decision = r["res"], r["decision"]
        st.divider()
        for note in r["notes"]:
            st.info(f"ℹ️ {note}")
        for alerte in r["alertes"]:
            st.warning(f"⚠️ {alerte}")

        # 1. BANDEAU INFO
        c1, c2, c3 = st.columns([1, 1, 2])
        color = ("risk-low" if res['r'] == "Faible"
                 else "risk-med" if res['r'] == "Modéré" else "risk-high")
        c1.markdown(f"Risque course : <span class='{color}'>{res['r']}</span>", unsafe_allow_html=True)
        c2.write(f"📍 {res['d']} | {res['m']} | {r['discipline']}")
        c3.info(f"🏁 Ordre IA : **{' - '.join(c['num'] for c in res['chevaux'][:3])}**")

        # 2. PODIUM : probabilité IA comparée à celle des cotes
        st.divider()
        marche = {l["num"]: l["proba_marche"] for _, l in decision["analyse"].iterrows()}
        cols = st.columns(5)
        meds = ["🥇 1er", "🥈 2ème", "🥉 3ème", "🏇 4ème", "🏇 5ème"]
        for col, med, c in zip(cols, meds, res["chevaux"][:5]):
            col.metric(f"{med} 🔥 OUT" if c["out"] else med, f"{c['num']} - {c['nom']}")
            col.caption(f"IA **{pct(c['p'])}** · cotes {pct(marche.get(c['num']))}")

        # 3. DÉCISION
        st.divider()
        pari = decision["pari"]
        if decision["jouer"]:
            cote_min = (1 + tl.PROFILS[r["profil"]]["ev_min"]) / pari["proba_retenue"]
            st.success(f"✅ **Pari conseillé : Simple Gagnant n° {pari['num']} {pari['nom']}** "
                       f"| cote {pari['cote']:g} | Mise : **{pari['mise']:.2f} €** "
                       f"({pari['fraction']:.1%} du capital, profil {r['profil']})")
            st.caption(f"Probabilité retenue {pct(pari['proba_retenue'])} (IA {pct(pari['proba_ia'])}, "
                       f"cotes {pct(pari['proba_marche'])}) → gain espéré **{pari['gain_espere']:+.0%}** "
                       f"par euro misé. Les cotes bougent jusqu'au départ : ne jouez que si la cote "
                       f"reste **≥ {cote_min:.1f}**.")
        else:
            st.warning(f"🚫 **Pas de pari conseillé.** {decision['raison']}")
        if res["combine"]:
            st.caption(f"💡 Idée de combiné de l'IA : {res['combine']['nom']} {res['combine']['nums']} — "
                       "son gain ne peut pas être mesuré (rapports inconnus), donc aucune mise n'est conseillée.")

        with st.expander("📊 Analyse de valeur de tous les partants"):
            tableau = decision["analyse"].rename(columns={
                "num": "N°", "nom": "Cheval", "cote": "Cote", "proba_ia": "Proba IA",
                "proba_marche": "Proba cotes", "proba_retenue": "Proba retenue", "gain_espere": "Gain espéré"})
            st.dataframe(tableau, hide_index=True, width="stretch", column_config={
                c: st.column_config.NumberColumn(c, format="percent")
                for c in ("Proba IA", "Proba cotes", "Proba retenue", "Gain espéré")})
            st.caption(f"Probabilité retenue = moyenne entre l'IA et les cotes ({tl.CONFIANCE_IA:.0%} IA). "
                       "Gain espéré = probabilité retenue × cote − 1.")
        st.caption("Les probabilités de l'IA sont des estimations, pas une garantie. "
                   "Suivez vos résultats dans l'onglet Historique.")

        if conn is not None and decision["jouer"]:
            if r["enregistre"]:
                st.success("✅ Ticket enregistré dans l'historique.")
            elif st.button("💾 Enregistrer le ticket"):
                try:
                    histo, existe = lire_historique(conn)
                    ligne = tl.ligne_historique(r["date"], r["hippo"], r["discipline"], r["profil"], pari)
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
        perte_7j = tl.pertes_recentes(histo, pd.Timestamp.now())
        m = st.columns(6)
        m[0].metric("Tickets", f"{stats['nb_tickets']} ({stats['nb_resolus']} joués)")
        m[1].metric("Réussite", f"{stats['reussite']:.0f} %")
        m[2].metric("Misé", f"{stats['mise_totale']:.2f} €")
        m[3].metric("Bénéfice", f"{stats['benefice']:+.2f} €")
        m[4].metric("ROI", f"{stats['roi']:+.1f} %")
        m[5].metric("Perte 7 jours", f"{max(perte_7j, 0):.2f} €"
                    + (f" / {limite_pertes} €" if limite_pertes else ""))

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
st.caption("Pari conseillé uniquement si la valeur est mesurable | Recherche du jour | Historique Google Sheets")
