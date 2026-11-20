from datetime import datetime
from html import escape

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

    /* Verdict : lisible en thème clair comme sombre (couleurs semi-transparentes) */
    .tm-verdict { border-radius: 14px; padding: 18px 20px; margin: 8px 0 18px; border: 2px solid; }
    .tm-oui { border-color: #1e9e4a; background: rgba(30, 158, 74, .12); }
    .tm-non { border-color: #d9822b; background: rgba(217, 130, 43, .12); }
    .tm-titre { font-size: 1.7rem; font-weight: 800; letter-spacing: .02em; line-height: 1.2; }
    .tm-oui .tm-titre { color: #1e9e4a; }
    .tm-non .tm-titre { color: #d9822b; }
    .tm-pari { font-size: 1.2rem; font-weight: 700; margin-top: 6px; }
    .tm-chiffres { display: flex; flex-wrap: wrap; gap: 10px; margin: 14px 0 8px; }
    .tm-chiffres div { flex: 1 1 110px; background: rgba(127, 127, 127, .14); border-radius: 10px; padding: 8px 12px; }
    .tm-chiffres span { display: block; font-size: .8rem; opacity: .75; }
    .tm-chiffres b { font-size: 1.5rem; }
    .tm-chiffres small { display: block; font-size: .75rem; opacity: .75; }
    .tm-pourquoi { opacity: .85; margin-top: 6px; }

    /* Classement */
    .tm-ligne { padding: 8px 12px; border-radius: 10px; margin-bottom: 6px; border: 1px solid rgba(127, 127, 127, .25); }
    .tm-choisi { border: 2px solid #1e9e4a; background: rgba(30, 158, 74, .08); }
    .tm-tete { display: flex; align-items: baseline; gap: 8px; }
    .tm-rang { width: 1.4em; }
    .tm-num { font-weight: 800; min-width: 1.8em; text-align: center; background: rgba(127, 127, 127, .2); border-radius: 6px; }
    .tm-nom { font-weight: 700; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .tm-tag { font-size: .72rem; font-weight: 700; padding: 1px 6px; border-radius: 6px; white-space: nowrap; }
    .tm-tag-out { color: #d9822b; border: 1px solid #d9822b; }
    .tm-tag-pari { color: #1e9e4a; border: 1px solid #1e9e4a; }
    .tm-pct { font-weight: 800; font-size: 1.15rem; white-space: nowrap; }
    .tm-barre { position: relative; height: 8px; border-radius: 4px; background: rgba(127, 127, 127, .2); margin-top: 6px; }
    .tm-ia { height: 100%; border-radius: 4px; background: #3b82f6; }
    .tm-marche { position: absolute; top: -3px; width: 3px; height: 14px; background: currentColor; opacity: .75; border-radius: 2px; }
    .tm-sous { font-size: .8rem; opacity: .7; margin-top: 3px; }
    .tm-legende { font-size: .8rem; opacity: .7; margin: 2px 0 10px; }
    .tm-legende i { display: inline-block; vertical-align: middle; margin: 0 4px 0 2px; }
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
    return "—" if x is None or pd.isna(x) else f"{x * 100:.0f}\u00a0%"


def euros(x):
    return f"{x:.2f}\u00a0€".replace(".", ",")


def verdict_html(decision, profil):
    """Grand encadré en tête de résultat : à jouer ou pas, en une ligne."""
    pari = decision["pari"]
    if not decision["jouer"]:
        return (f'<div class="tm-verdict tm-non"><div class="tm-titre">🚫 NE PAS JOUER</div>'
                f'<div class="tm-pari">{escape(decision["raison"])}</div>'
                f'<div class="tm-pourquoi">{escape(decision["detail"] or "")}</div></div>')
    cote_min = (1 + tl.PROFILS[profil]["ev_min"]) / pari["proba_retenue"]
    part_capital = f"{pari['fraction'] * 100:.1f}".replace(".", ",")
    return f"""<div class="tm-verdict tm-oui">
<div class="tm-titre">✅ À JOUER</div>
<div class="tm-pari">Simple Gagnant · n° {escape(pari['num'])} {escape(pari['nom'])}</div>
<div class="tm-chiffres">
<div><span>Mise</span><b>{euros(pari['mise'])}</b><small>{part_capital}\u00a0% du capital</small></div>
<div><span>Cote</span><b>{pari['cote']:g}</b><small>à jouer si elle reste ≥ {cote_min:.1f}</small></div>
<div><span>Gain espéré</span><b>{pari['gain_espere'] * 100:+.0f}\u00a0%</b><small>par euro misé</small></div>
</div>
<div class="tm-pourquoi">Pourquoi : l'IA lui donne <b>{pct(pari['proba_ia'])}</b> de chances de gagner,
les cotes seulement <b>{pct(pari['proba_marche'])}</b>.</div>
</div>"""


def classement_html(res, decision):
    """Les 5 chevaux préférés de l'IA, avec une barre IA et un trait pour les cotes."""
    marche = {l["num"]: l["proba_marche"] for _, l in decision["analyse"].iterrows()}
    cotes = {l["num"]: l["cote"] for _, l in decision["analyse"].iterrows()}
    num_pari = decision["pari"]["num"] if decision["jouer"] else None
    top = res["chevaux"][:5]
    echelle = max([c["p"] for c in top] + [marche.get(c["num"]) or 0 for c in top]) or 1
    rangs = ["🥇", "🥈", "🥉", "4", "5"]
    lignes = []
    for rang, c in zip(rangs, top):
        q, cote = marche.get(c["num"]), cotes.get(c["num"])
        tags = ""
        if c["num"] == num_pari:
            tags += '<span class="tm-tag tm-tag-pari">PARI</span>'
        if c["out"]:
            tags += '<span class="tm-tag tm-tag-out">🔥 OUTSIDER</span>'
        trait = f'<div class="tm-marche" style="left:{q / echelle * 100:.1f}%"></div>' if q is not None else ""
        sous = " · ".join(x for x in [f"cotes {pct(q)}" if q is not None else "",
                                      f"cote {cote:g}" if cote else "pas de cote"] if x)
        lignes.append(
            f'<div class="tm-ligne{" tm-choisi" if c["num"] == num_pari else ""}">'
            f'<div class="tm-tete"><span class="tm-rang">{rang}</span><span class="tm-num">{escape(c["num"])}</span>'
            f'<span class="tm-nom">{escape(c["nom"])}</span>{tags}<span class="tm-pct">{pct(c["p"])}</span></div>'
            f'<div class="tm-barre"><div class="tm-ia" style="width:{c["p"] / echelle * 100:.1f}%"></div>{trait}</div>'
            f'<div class="tm-sous">{sous}</div></div>')
    legende = ('<div class="tm-legende">Chances de gagner : '
               '<i style="width:18px;height:8px;border-radius:4px;background:#3b82f6"></i>selon l\'IA, '
               '<i style="width:3px;height:12px;background:currentColor;opacity:.75"></i>selon les cotes</div>')
    return legende + "".join(lignes)


# --- 3. INTERFACE ---
st.title("🚀 TurfMaster 2.5 : Ultimate Investor")
st.caption("Collez la course : l'application vous dit **s'il faut jouer**, sur quel cheval et combien.")

with st.sidebar:
    hippo_input = st.text_input("Hippodrome", value="Vincennes")
    choix_discipline = st.selectbox("Discipline", [AUTO] + tl.DISCIPLINES)
    st.divider()
    capital = st.number_input("Capital (€)", value=1000, min_value=0)
    profil = st.select_slider("Profil de Risque", list(tl.PROFILS), value="Équilibré")
    regles = tl.PROFILS[profil]
    st.caption(f"Joue seulement si le gain espéré atteint **{regles['ev_min'] * 100:+.0f}\u00a0%** "
               f"et la cote **≤ {regles['cote_max']}**. Mise max **{regles['plafond']:.0%}** du capital.")
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

    if st.button("⚡ ANALYSER LA COURSE", width="stretch"):
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
        pari = decision["pari"]

        # 1. LE VERDICT, en gros
        st.markdown(verdict_html(decision, r["profil"]), unsafe_allow_html=True)
        for alerte in r["alertes"]:
            st.warning(f"⚠️ {alerte}")
        for note in r["notes"]:
            st.caption(f"ℹ️ {note}")

        # 2. LE CLASSEMENT
        st.markdown("#### 🏁 Classement de l'IA")
        st.markdown(classement_html(res, decision), unsafe_allow_html=True)
        st.caption(f"{r['discipline']} · {r['hippo']} · météo {res['m']} · distance {res['d']} · "
                   f"course jugée : {res['r']}")

        # 3. LE DÉTAIL, pour qui veut comprendre
        with st.expander("🔍 Détails du calcul"):
            if res["combine"]:
                st.markdown(f"💡 **Idée de combiné de l'IA : {res['combine']['nom']} "
                            f"{res['combine']['nums']}** — non conseillé : son gain ne peut pas être "
                            "mesuré sans les rapports.")
            tableau = decision["analyse"].rename(columns={
                "num": "N°", "nom": "Cheval", "cote": "Cote", "proba_ia": "Proba IA",
                "proba_marche": "Proba cotes", "proba_retenue": "Proba retenue", "gain_espere": "Gain espéré"})
            st.dataframe(tableau, hide_index=True, width="stretch", column_config={
                c: st.column_config.NumberColumn(c, format="percent")
                for c in ("Proba IA", "Proba cotes", "Proba retenue", "Gain espéré")})
            st.caption(f"Proba retenue = moyenne entre l'IA et les cotes. Gain espéré = proba retenue × cote − 1. "
                       f"Règles du profil {r['profil']} : {tl.decrire_profil(r['profil'])}. "
                       "Les probabilités de l'IA sont des estimations, pas une garantie.")

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
