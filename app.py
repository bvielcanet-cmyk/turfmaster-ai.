import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
import json
from html import escape

import pandas as pd
import streamlit as st

import mesure
import place
import protection
import plan
import pmu
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
    .tm-place { border-color: #2563eb; background: rgba(37, 99, 235, .10); }
    .tm-place .tm-titre { color: #3b82f6; }
    .tm-neutre { border-color: rgba(127, 127, 127, .5); background: rgba(127, 127, 127, .08); }
    .tm-neutre .tm-titre { font-size: 1.15rem; opacity: .8; }
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
    .tm-presse { background: #8b5cf6; }
    .tm-joker { border: 2px dashed #d9822b; }
    .tm-rouge { border-color: #dc2626; background: rgba(220, 38, 38, .10); }
    .tm-rouge .tm-titre { color: #ef4444; }
    .tm-sources a { margin-right: 10px; }
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
FEUILLE_ANALYSES = "Analyses"  # onglet où sont rangées toutes les analyses (mesure de précision)
FEUILLE_SUIVI = "ConseilsPlace"  # onglet du suivi à blanc des conseils Simple Placé
AUTO = "Auto (d'après la musique)"


# --- 2. SERVICES ---

@st.cache_resource
def memoire_recherches():
    """Mémoire partagée des recherches Google : {clé: (heure, résultat)}.
    Utilisable depuis plusieurs fils d'exécution (les deux recherches tournent en parallèle)."""
    return {}


def en_memoire(memoire, cle, duree, calcul):
    """Renvoie le résultat gardé en mémoire s'il a moins de `duree` secondes, sinon le calcule.
    Les erreurs ne sont pas gardées."""
    deja = memoire.get(cle)
    if deja and time.time() - deja[0] < duree:
        return deja[1]
    resultat = calcul()
    memoire[cle] = (time.time(), resultat)
    return resultat


@st.cache_data(ttl=3600, show_spinner=False)
def analyser_course(partants_str, hippo, discipline, profil, contexte, presse, _api_key):
    """Analyse mise en cache 1 h : recoller la même course ne consomme pas de quota.
    Les erreurs (exceptions) ne sont jamais mises en cache."""
    return tl.analyser(_api_key, tl.construire_prompt(partants_str, hippo, discipline, profil, contexte, presse))


def lancer_recherches(hippo, discipline, partants_str, avec_contexte, avec_presse, course=""):
    """Recherche du jour (météo, terrain) et pronostics publiés, en parallèle.
    Retourne {"contexte": texte ou GeminiErreur, "presse": (texte, sources) ou GeminiErreur}."""
    memoire = memoire_recherches()
    jour = datetime.now().strftime("%d/%m/%Y")
    taches = {}
    if avec_contexte:
        taches["contexte"] = (("contexte", hippo, discipline, jour), 6 * 3600,
                              lambda: tl.rechercher_contexte(API_KEY, hippo, discipline, jour))
    if avec_presse:
        noms = "\n".join(l.split(" (")[0] for l in partants_str.splitlines())
        taches["presse"] = (("presse", hippo, jour, noms), 3 * 3600,
                            lambda: tl.rechercher_pronostics(API_KEY, hippo, discipline, jour, noms, course))
    resultats = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futurs = {nom: pool.submit(en_memoire, memoire, *t) for nom, t in taches.items()}
        for nom, futur in futurs.items():
            try:
                resultats[nom] = futur.result()
            except tl.GeminiErreur as e:
                resultats[nom] = e
    return resultats


def connexion_sheets():
    """Retourne (connexion, message). La connexion est None si Google Sheets n'est pas configuré."""
    try:
        cfg = st.secrets.get("connections", {}).get("gsheets")
    except Exception:
        cfg = None
    if not cfg:
        return None, None
    if cfg.get("type") != "service_account":
        return None, "Google Sheets ignoré : il faut un compte de service Google (voir le README)."
    try:
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection), None
    except Exception:
        return None, "Connexion au Google Sheet impossible : vérifiez les Secrets."


def expliquer_erreur_sheets(erreur):
    """Traduit une erreur Google Sheets en cause compréhensible (sans jamais afficher de clé)."""
    nom, texte = type(erreur).__name__, str(erreur)
    bas = texte.lower()
    if "has not been used" in bas or "service_disabled" in bas or "is disabled" in bas:
        return ("Une API Google n'est pas activée : activez **Google Sheets API** et **Google Drive API** "
                "dans le projet Google Cloud du compte de service.")
    if nom == "SpreadsheetNotFound" or "not found" in bas or "404" in texte:
        return ("Classeur introuvable : vérifiez l'adresse `spreadsheet` dans les Secrets, et que le classeur "
                "est **partagé avec l'adresse du compte de service**.")
    if "permission" in bas or "403" in texte:
        return ("Accès refusé : partagez le classeur avec l'adresse `client_email` du compte de service, "
                "en **Éditeur**.")
    if "invalid_grant" in bas or "jwt" in bas or "deserialize" in bas or "private key" in bas or "pem" in bas:
        return ("Clé du compte de service invalide : recopiez `private_key` (avec ses `\\n`) et les autres "
                "valeurs du fichier JSON dans les Secrets.")
    if "spreadsheet" in bas and ("must" in bas or "missing" in bas or "required" in bas):
        return "Adresse du classeur absente : ajoutez `spreadsheet = \"https://docs.google.com/...\"` dans les Secrets."
    return f"Erreur Google Sheets ({nom}) : {texte[:200]}"


class Stockage:
    """Tickets et analyses : dans Google Sheets s'il est configuré, sinon dans des fichiers CSV
    locaux (perdus à chaque redémarrage sur Streamlit Cloud)."""

    def __init__(self, conn):
        self.conn = conn
        self.derniere_erreur = None  # cause lisible de la dernière erreur Google Sheets
        self.dossier = Path(os.environ.get("TURFMASTER_DONNEES", Path(__file__).parent / "donnees_locales"))

    @property
    def local(self):
        return self.conn is None

    def lire(self, feuille, colonnes):
        """Retourne (DataFrame, existe)."""
        try:
            if self.local:
                chemin = self.dossier / f"{feuille}.csv"
                if not chemin.exists():
                    return pd.DataFrame(columns=colonnes), False
                df = pd.read_csv(chemin, dtype={"chevaux": str, "pari_num": str, "gagnant": str, "course": str,
                                                "date_course": str, "analyse": str, "id": str},
                                 keep_default_na=False)
            else:
                df = self.conn.read(worksheet=feuille, ttl=0)
        except Exception as e:
            if not self.local and type(e).__name__ != "WorksheetNotFound":  # onglet absent = normal au début
                self.derniere_erreur = expliquer_erreur_sheets(e)
            return pd.DataFrame(columns=colonnes), False
        df = df.dropna(how="all")
        for col in colonnes:
            if col not in df.columns:
                df[col] = ""
        return mesure.normaliser(df[colonnes]), True

    def ecrire(self, feuille, df, existe):
        if self.local:
            self.dossier.mkdir(parents=True, exist_ok=True)
            df.to_csv(self.dossier / f"{feuille}.csv", index=False)
            return
        try:
            if existe:
                self.conn.update(worksheet=feuille, data=df)
            else:
                self.conn.create(worksheet=feuille, data=df)
        except Exception as e:
            self.derniere_erreur = expliquer_erreur_sheets(e)
            raise


@st.cache_data(ttl=300, show_spinner=False)
def programme_pmu(jour):
    return pmu.programme(jour)


@st.cache_data(ttl=60, show_spinner=False)
def partants_pmu(jour, reunion, course):
    return pmu.partants(jour, reunion, course)


@st.cache_data(ttl=60, show_spinner=False)
def cotes_place_pmu(jour, reunion, course):
    return pmu.cotes_place(jour, reunion, course)


def calculer_conseil_place(stockage, course_pmu, jour, df, profil, capital, budget):
    """Conseil Simple Placé (sans IA) ; enregistré dans le suivi à blanc si la course n'est pas partie.
    Retourne {"conseil", "note"}."""
    try:
        conseil = place.conseil_place(df, cotes_place_pmu(jour, course_pmu["reunion"], course_pmu["course"]),
                                      profil, capital, budget)
    except pmu.PmuErreur as e:
        return {"conseil": None, "note": f"Cotes du Placé indisponibles ({e})."}
    if conseil is None:
        return {"conseil": None, "note": None}
    if course_pmu["statut"] != "à venir" or pmu.depart_passe(course_pmu, jour):
        return {"conseil": conseil, "note": "Course déjà partie : ce conseil n'est pas compté dans le suivi à blanc."}
    try:
        suivi, existe = stockage.lire(FEUILLE_SUIVI, place.COLONNES_SUIVI)
        ligne = place.ligne_suivi("P" + datetime.now().strftime("%Y%m%d%H%M%S%f"),
                                  datetime.now().strftime("%Y-%m-%d %H:%M"), pmu.date_pmu(jour), course_pmu["id"],
                                  course_pmu["hippodrome"], conseil)
        stockage.ecrire(FEUILLE_SUIVI, place.ajouter_suivi(suivi, ligne), existe)
        note = None
    except Exception:
        note = "Conseil non enregistré dans le suivi. " + (stockage.derniere_erreur or "")
    return {"conseil": conseil, "note": note}


def conseil_place_html(c, profil):
    if c is None:
        return ('<div class="tm-verdict tm-neutre"><div class="tm-titre">🎯 Pas de Placé intéressant</div>'
                '<div class="tm-pourquoi">Aucun Simple Placé de cette course n\'a une cote assez généreuse '
                'par rapport à ses chances.</div></div>')
    return f"""<div class="tm-verdict tm-place">
<div class="tm-titre">🎯 PLACÉ CONSEILLÉ</div>
<div class="tm-pari">Simple Placé · n° {escape(c['num'])} {escape(c['nom'])}</div>
<div class="tm-chiffres">
<div><span>Mise ({escape(profil)})</span><b>{euros(c['mise'])}</b><small>mise fixe, en test</small></div>
<div><span>Cote Placé probable</span><b>{c['cote_min']:g} – {c['cote_max']:g}</b><small>jouer seulement si le minimum reste ≥ {c['cote_mini_a_jouer']:.2f}</small></div>
<div><span>Gain espéré</span><b>{c['gain_espere'] * 100:+.0f}\u00a0%</b><small>calcul souvent optimiste</small></div>
</div>
<div class="tm-pourquoi">Chances de placé estimées ≈ <b>{c['proba_corrigee']:.0%}</b> (formule corrigée, plus réaliste).<br>
🧪 <b>Phase de test (suivi à blanc)</b> : ce conseil est noté et sera réglé automatiquement
au rapport officiel. Ne misez pas avant d'avoir vu le bilan dans l'onglet Historique.</div>
</div>"""


def tester_courses_passees(stockage, profil, capital, confiance, nombre=5, jours=7):
    """Analyse `nombre` courses françaises déjà courues (jours précédents), sans recherche internet,
    et les enregistre avec leur gagnant officiel : la mesure de précision avance d'autant.
    Retourne un message de compte rendu."""
    analyses, existe = stockage.lire(FEUILLE_ANALYSES, mesure.COLONNES_ANALYSES)
    deja = {(mesure.texte_cellule(a["date_course"]).zfill(8), a["course"]) for _, a in analyses.iterrows()}
    candidates = []
    for k in range(1, jours + 1):
        jour = date.today() - pd.Timedelta(days=k)
        try:
            for c in programme_pmu(jour):
                if (c["pays"] == "FRA" and c["statut"] == "terminée" and c["arrivee"]
                        and (pmu.date_pmu(jour), c["id"]) not in deja):
                    candidates.append((jour, c))
        except pmu.PmuErreur:
            continue
    random.shuffle(candidates)  # courses variées (jours, hippodromes, disciplines)

    testees, chances_ia, chances_cotes, arret = 0, [], [], None
    for jour, c in candidates:
        if testees >= nombre:
            break
        try:
            df = partants_pmu(jour, c["reunion"], c["course"])
            if df.empty or df["COTE"].isna().any():
                continue
            partants_str = "\n".join(f"{row['FULL_ID']} ({row['Info']})" for _, row in df.iterrows())
            raw = analyser_course(partants_str, c["hippodrome"], c["discipline"], profil, None, None, API_KEY)
            res, _ = tl.valider_reponse(tl.extraire_json(raw), df)
        except tl.GeminiErreur as e:
            arret = str(e)
            break
        except (pmu.PmuErreur, ValueError, KeyError, TypeError):
            continue
        decision = tl.evaluer_pari(res["chevaux"], df, capital, profil, None, confiance)
        ligne = mesure.ligne_analyse("T" + datetime.now().strftime("%Y%m%d%H%M%S%f"),
                                     datetime.now().strftime("%Y-%m-%d %H:%M"), pmu.date_pmu(jour), c["id"],
                                     c["hippodrome"], c["discipline"], profil, decision)
        ligne["gagnant"], ligne["source_resultat"] = c["arrivee"][0], "PMU officiel (test sur course passée)"
        analyses = mesure.ajouter_analyse(analyses, ligne)
        partants = json.loads(ligne["partants"])
        gagnant = partants.get(c["arrivee"][0], {})
        chances_ia.append(gagnant.get("ia") or 0)
        chances_cotes.append(gagnant.get("cotes") or 0)
        testees += 1

    if testees:
        stockage.ecrire(FEUILLE_ANALYSES, analyses, existe)
        message = (f"{testees} course(s) passée(s) testée(s). Chances données au gagnant, en moyenne : "
                   f"IA {sum(chances_ia) / testees:.0%}, cotes {sum(chances_cotes) / testees:.0%}.")
    else:
        message = "Aucune course passée testée."
    if arret:
        message += f" Arrêt : {arret}"
    elif not candidates:
        message += " Plus aucune course passée à tester sur les 7 derniers jours."
    return message


def recuperer_arrivees(stockage, avec_gemini, maximum_gemini=5):
    """Cherche le gagnant des analyses en attente et met à jour les tickets.
    Retourne un message de compte rendu."""
    analyses, existe_a = stockage.lire(FEUILLE_ANALYSES, mesure.COLONNES_ANALYSES)
    attente = mesure.en_attente(analyses)
    memo = {}

    def arrivee_pmu(date_course, course_id):  # une seule requête par course, même si plusieurs lignes
        cle = (date_course, course_id)
        if cle not in memo:
            reunion, course = pmu.decouper_id(course_id)
            memo[cle] = pmu.arrivee(date_course.zfill(8), reunion, course)
        return memo[cle]

    trouves, pas_finies, gemini_utilises, erreurs = 0, 0, 0, []
    for i, a in attente.iterrows():
        try:
            if a["course"]:
                arr = arrivee_pmu(a["date_course"], a["course"])
                if arr["annulee"]:
                    analyses.at[i, "gagnant"], analyses.at[i, "source_resultat"] = "annulée", "PMU officiel"
                    trouves += 1
                elif arr["terminee"]:
                    rapport = arr["rapports_gagnant"].get(arr["gagnant"])
                    analyses.at[i, "gagnant"] = arr["gagnant"]
                    analyses.at[i, "source_resultat"] = f"PMU officiel : {rapport}" if rapport else "PMU officiel"
                    trouves += 1
                else:
                    pas_finies += 1
            elif avec_gemini and gemini_utilises < maximum_gemini:
                gemini_utilises += 1
                partants = json.loads(a["partants"])
                noms = "\n".join(f"{n} - {v['nom']}" for n, v in partants.items())
                jour = pd.to_datetime(a["date"]).strftime("%d/%m/%Y")
                gagnant = tl.rechercher_arrivee(API_KEY, jour, a["hippodrome"], noms)
                if gagnant in partants:
                    analyses.at[i, "gagnant"] = gagnant
                    analyses.at[i, "source_resultat"] = "recherche Gemini (non officiel)"
                    trouves += 1
        except (pmu.PmuErreur, tl.GeminiErreur) as e:
            erreurs.append(str(e))
        except (ValueError, KeyError, TypeError):
            erreurs.append(f"Analyse {a['id']} illisible.")
    if trouves:
        stockage.ecrire(FEUILLE_ANALYSES, analyses, existe_a)
        tickets, existe_t = stockage.lire(FEUILLE, tl.COLONNES_HISTORIQUE)
        tickets, modifies = mesure.mettre_a_jour_tickets(tickets, analyses)
        if modifies:
            stockage.ecrire(FEUILLE, tickets, existe_t)
    else:
        modifies = 0

    # Conseils Placé du suivi à blanc
    suivi, existe_s = stockage.lire(FEUILLE_SUIVI, place.COLONNES_SUIVI)
    regles = 0
    for i, c in suivi[suivi["resultat"] == "En attente"].iterrows():
        try:
            regles += place.regler(suivi, i, arrivee_pmu(c["date_course"], c["course"]))
        except (pmu.PmuErreur, ValueError) as e:
            erreurs.append(str(e))
    if regles:
        stockage.ecrire(FEUILLE_SUIVI, suivi, existe_s)

    morceaux = [f"{trouves} arrivée(s) récupérée(s)", f"{modifies} ticket(s) mis à jour",
                f"{regles} conseil(s) Placé réglé(s)"]
    if pas_finies:
        morceaux.append(f"{pas_finies} course(s) pas encore terminée(s)")
    restantes = len(attente) - trouves - pas_finies
    if restantes > 0:
        morceaux.append(f"{restantes} course(s) collée(s) sans résultat"
                        + ("" if avec_gemini else " (cochez la recherche Gemini)"))
    return " · ".join(morceaux) + "." + (f" Erreurs : {' ; '.join(sorted(set(erreurs)))}" if erreurs else "")


def pct(x):
    return "—" if x is None or pd.isna(x) else f"{x * 100:.0f}\u00a0%"


def euros(x):
    return f"{x:.2f}\u00a0€".replace(".", ",")


def avis_presse(num, compil):
    """« cité par 3 sources sur 5 (1er choix de 2) », ou None sans pronostics."""
    if not compil or not compil["sources"]:
        return None
    n = len(compil["sources"])
    e = next((e for e in compil["consensus"] if e["num"] == num), None)
    if e is None:
        return f"cité par aucune des {n} sources"
    texte = f"cité par {e['citations']} source{'s' if e['citations'] > 1 else ''} sur {n}"
    return texte + (f" (1er choix de {e['premier']})" if e["premier"] else "")


def verdict_html(decision, profil, compil=None):
    """Grand encadré en tête de résultat : à jouer ou pas, en une ligne."""
    pari = decision["pari"]
    if not decision["jouer"]:
        return (f'<div class="tm-verdict tm-non"><div class="tm-titre">🚫 NE PAS JOUER</div>'
                f'<div class="tm-pari">{escape(decision["raison"])}</div>'
                f'<div class="tm-pourquoi">{escape(decision["detail"] or "")}</div></div>')
    cote_min = (1 + tl.PROFILS[profil]["ev_min"]) / pari["proba_retenue"]
    part_capital = f"{pari['fraction'] * 100:.1f}".replace(".", ",")
    avis = avis_presse(pari["num"], compil)
    ligne_presse = ""
    if avis:
        alerte = " ⚠️" if avis.startswith("cité par aucune") else ""
        ligne_presse = f"<br>📰 Pronostiqueurs : <b>{escape(avis)}</b>{alerte}."
    return f"""<div class="tm-verdict tm-oui">
<div class="tm-titre">✅ À JOUER</div>
<div class="tm-pari">Simple Gagnant · n° {escape(pari['num'])} {escape(pari['nom'])}</div>
<div class="tm-chiffres">
<div><span>Mise</span><b>{euros(pari['mise'])}</b><small>{part_capital}\u00a0% du capital</small></div>
<div><span>Cote</span><b>{pari['cote']:g}</b><small>à jouer si elle reste ≥ {cote_min:.1f}</small></div>
<div><span>Gain espéré</span><b>{pari['gain_espere'] * 100:+.0f}\u00a0%</b><small>par euro misé</small></div>
</div>
<div class="tm-pourquoi">Pourquoi : l'IA lui donne <b>{pct(pari['proba_ia'])}</b> de chances de gagner,
les cotes seulement <b>{pct(pari['proba_marche'])}</b>.{ligne_presse}</div>
</div>"""


def classement_html(res, decision, compil=None):
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
                                      f"cote {cote:g}" if cote else "pas de cote",
                                      f"📰 {avis_presse(c['num'], compil)}" if avis_presse(c['num'], compil) else ""] if x)
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


def presse_html(compil):
    """Consensus des pronostiqueurs : une ligne par cheval cité, barre = points."""
    n = len(compil["sources"])
    maxi = max(e["points"] for e in compil["consensus"])
    lignes = []
    for e in compil["consensus"][:6]:
        premier = f" · 1er choix de {e['premier']}" if e["premier"] else ""
        lignes.append(
            f'<div class="tm-ligne"><div class="tm-tete"><span class="tm-num">{escape(e["num"])}</span>'
            f'<span class="tm-nom">{escape(e["nom"])}</span><span class="tm-pct">{e["points"]}\u00a0pts</span></div>'
            f'<div class="tm-barre"><div class="tm-ia tm-presse" style="width:{e["points"] / maxi * 100:.1f}%"></div></div>'
            f'<div class="tm-sous">cité par {e["citations"]}/{n}{premier}</div></div>')
    return "".join(lignes)


def plan_html(sel, jok, budget, profil):
    if sel.empty or sel["mise"].sum() == 0:
        corps = ('<div class="tm-verdict tm-neutre"><div class="tm-titre">📅 Aucune course prometteuse pour '
                 f'le profil {escape(profil)}</div><div class="tm-pourquoi">Mieux vaut ne rien jouer que forcer un '
                 'pari. Relancez l\'analyse plus tard : les cotes bougent au fil de la journée.</div></div>')
    else:
        lignes = []
        for _, r in sel.iterrows():
            if r["mise"] <= 0:
                continue
            lignes.append(
                f'<div class="tm-ligne"><div class="tm-tete"><span class="tm-num">{escape(r["heure"])}</span>'
                f'<span class="tm-nom">{escape(r["course"])} {escape(r["hippodrome"])} — Placé n° {escape(r["num"])} '
                f'{escape(r["nom"])}</span><span class="tm-pct">{euros(r["mise"])}</span></div>'
                f'<div class="tm-sous">cote Placé {r["cote_min"]:g}–{r["cote_max"]:g} · jouer si ≥ '
                f'{r["cote_mini_a_jouer"]:.2f} · chances de placé ≈ {r["proba_corrigee"]:.0%} · '
                f'valeur {r["valeur"] * 100:+.0f}\u00a0%</div></div>')
        corps = "".join(lignes)
    if jok:
        corps += (f'<div class="tm-ligne tm-joker"><div class="tm-tete"><span class="tm-num">{escape(jok["heure"])}</span>'
                  f'<span class="tm-nom">🃏 Joker : {escape(jok["course"])} {escape(jok["hippodrome"])} — Placé n° '
                  f'{escape(jok["num"])} {escape(jok["nom"])}</span><span class="tm-pct">{euros(jok["mise"])}</span></div>'
                  f'<div class="tm-sous">outsider (cote Gagnant {jok["cote_gagnant"]:g}) · cote Placé '
                  f'{jok["cote_min"]:g}–{jok["cote_max"]:g} · jouer si ≥ {jok["cote_mini_a_jouer"]:.2f} · '
                  f'<b>non prouvé, très variable</b></div></div>')
    total = (sel["mise"].sum() if not sel.empty else 0) + (jok["mise"] if jok else 0)
    return corps + (f'<div class="tm-legende">Total : <b>{euros(total)}</b> sur {euros(budget)} · profil '
                    f'{escape(profil)} · plan provisoire : reconfirmez chaque pari 5 à 10 minutes avant le départ '
                    '(cote Placé minimale ≥ seuil indiqué).</div>')


def feu_html(bilan, budget):
    """Encadré du feu tricolore du mode one shot."""
    titre = {"vert": "🟢 JEU POSSIBLE", "orange": "🟠 RISQUE ÉLEVÉ", "rouge": "🔴 NE PAS JOUER AUJOURD'HUI"}
    classe = {"vert": "tm-oui", "orange": "tm-non", "rouge": "tm-rouge"}
    if bilan["feu"] == "rouge" and "risque_tout_perdre" in bilan:
        corps = (f'<div class="tm-pari">{escape(bilan["raison"][:1].upper() + bilan["raison"][1:])} : environ '
                 f'{bilan["risque_tout_perdre"] * 100:.0f}\u00a0% de risque de tout perdre.</div>'
                 '<div class="tm-pourquoi">Mieux vaut garder le budget pour un autre jour. Relancez l\'analyse plus '
                 'tard : les cotes bougent au fil de la journée.</div>')
    elif "risque_tout_perdre" not in bilan:
        corps = (f'<div class="tm-pari">{escape(bilan["raison"][:1].upper() + bilan["raison"][1:])}.</div>'
                 '<div class="tm-pourquoi">Mieux vaut garder le budget pour un autre jour. Relancez l\'analyse plus '
                 'tard : les cotes bougent au fil de la journée.</div>')
    else:
        gain_txt, gain_note = (("≈ 2 sur 3", "moyenne des plans passés de ce type") if bilan["feu"] == "vert"
                               else ("moins de 2 sur 3", "plan plus risqué que la moyenne"))
        corps = f"""<div class="tm-pari">{escape(bilan['raison'][:1].upper() + bilan['raison'][1:])} · {bilan['n']} Placés · {euros(bilan['total'])} misés</div>
<div class="tm-chiffres">
<div><span>Risque de tout perdre</span><b>≈ {bilan['risque_tout_perdre'] * 100:.0f}\u00a0%</b><small>estimation corrigée</small></div>
<div><span>Finir en gain</span><b>{gain_txt}</b><small>{gain_note}</small></div>
<div><span>Gain espéré</span><b>{bilan['gain_espere'] * 100:+.0f}\u00a0%</b><small>calcul souvent optimiste</small></div>
</div>
<div class="tm-pourquoi">Mises réparties pour <b>maximiser les chances de finir en gain</b> (plus sur le Placé le plus
sûr). Budget de {euros(budget)} joué une fois : vous pouvez le perdre entièrement.</div>"""
    return f'<div class="tm-verdict {classe[bilan["feu"]]}"><div class="tm-titre">{titre[bilan["feu"]]}</div>{corps}</div>'


def avis_ia(course_row, df, profil):
    """Avis de l'IA (1 requête Gemini, sans recherche) sur le cheval retenu : compare ses chances de victoire
    selon l'IA et selon les cotes. Informatif : ne change pas le pari."""
    partants_str = "\n".join(f"{row['FULL_ID']} ({row['Info']})" for _, row in df.iterrows())
    raw = analyser_course(partants_str, course_row["hippodrome"], course_row["discipline"], profil, None, None, API_KEY)
    res, _ = tl.valider_reponse(tl.extraire_json(raw), df)
    ia = {c["num"]: c["p"] for c in res["chevaux"]}
    marche = tl.probas_marche(df) or {}
    p_ia, q = ia.get(str(course_row["num"]), 0.0), marche.get(str(course_row["num"]), 0.0)
    if q and p_ia >= 1.15 * q:
        avis = "👍 l'IA lui donne plus de chances que les cotes"
    elif q and p_ia <= 0.85 * q:
        avis = "⚠️ l'IA lui donne moins de chances que les cotes : prudence"
    else:
        avis = "➖ l'IA est d'accord avec les cotes"
    return f"{avis} (victoire : IA {pct(p_ia)}, cotes {pct(q)})"


# --- 3. INTERFACE ---
st.title("🚀 TurfMaster 2.5 : Ultimate Investor")
st.caption("Choisissez une course : l'application vous dit **s'il faut jouer**, sur quel cheval et combien.")

with st.sidebar:
    choix_discipline = st.selectbox("Discipline", [AUTO] + tl.DISCIPLINES)
    st.divider()
    capital_depart = st.number_input("Capital de départ (€)", value=1000, min_value=0,
                                     help="Le capital actuel en est déduit avec vos résultats (tickets joués, "
                                          "ou suivi à blanc tant que vous ne jouez pas).")
    profil = st.select_slider("Profil de Risque", list(tl.PROFILS), value="Équilibré")
    regles = tl.PROFILS[profil]
    st.caption(f"Joue seulement si le gain espéré atteint **{regles['ev_min'] * 100:+.0f}\u00a0%** "
               f"et la cote **≤ {regles['cote_max']}**. Mise max **{regles['plafond']:.0%}** du capital.")
    limite_pertes = st.number_input("Perte max sur 7 jours (€, 0 = sans limite)", value=100, min_value=0,
                                    help="Vérifiée avec l'historique des tickets.")
    recherche = st.toggle("🔎 Recherche Google (météo, terrain, distance)", value=True,
                          help="Faite une fois par hippodrome et par jour, puis réutilisée.")
    avec_presse = st.toggle("📰 Pronostics de la presse", value=True,
                            help="Cherche les pronostics publiés pour la course et les compile. "
                                 "Seules les sources réellement trouvées par la recherche sont gardées.")
    if st.button("🧹 Reset"):
        st.session_state.pop("resultat", None)
        st.rerun()

conn, message_sheets = connexion_sheets()
stockage = Stockage(conn)
analyses_enregistrees, _ = stockage.lire(FEUILLE_ANALYSES, mesure.COLONNES_ANALYSES)
precision = mesure.scores(analyses_enregistrees)
confiance, confiance_mesuree = mesure.confiance_ia(precision, tl.CONFIANCE_IA)

# Protection automatique des mises : capital actuel et réduction après une baisse de plus de 15 %
etat_capital = protection.etat_courant(capital_depart, stockage.lire(FEUILLE, tl.COLONNES_HISTORIQUE)[0],
                                       stockage.lire(FEUILLE_SUIVI, place.COLONNES_SUIVI)[0])
capital = etat_capital["capital"] * etat_capital["facteur"]  # capital servant au calcul des mises
with st.sidebar:
    if etat_capital["reduit"]:
        st.warning(f"🛡️ Protection active : capital {euros(etat_capital['capital'])}, "
                   f"{etat_capital['baisse']:.0%} sous son plus haut ({euros(etat_capital['pic'])}). "
                   "Mises divisées par 2 jusqu'à ce qu'il remonte.")
    else:
        st.caption(f"🛡️ Capital actuel : **{euros(etat_capital['capital'])}** (plus haut "
                   f"{euros(etat_capital['pic'])}, d'après le {etat_capital['source']}). Les mises seront "
                   f"divisées par 2 si le capital baisse de plus de {protection.SEUIL_BAISSE:.0%}.")
# La clé garde l'onglet ouvert quand la page se recharge (après un clic sur un bouton)
onglet_prono, onglet_plan, onglet_histo = st.tabs(["🎯 Pronostic", "📅 Plan du jour", "📊 Historique"],
                                                  key="onglet")

with onglet_prono:
    PMU, COLLE = "📅 Programme PMU", "📋 Copier-coller"
    source = st.radio("Partants", [PMU, COLLE], horizontal=True, label_visibility="collapsed")
    course_pmu, jour = None, date.today()
    if source == PMU:
        jour = st.date_input("Jour", value=date.today(), format="DD/MM/YYYY")
        try:
            courses = programme_pmu(jour)
        except pmu.PmuErreur as e:
            st.error(f"❌ {e}")
            courses = []
        if courses:
            a_venir = next((i for i, c in enumerate(courses) if c["statut"] == "à venir"), 0)
            course_pmu = st.selectbox("Course", courses, index=a_venir, format_func=pmu.libelle_course)
            if course_pmu["statut"] == "terminée":
                st.caption("ℹ️ Course terminée : l'analyse se fait sans recherche internet (pour ne pas "
                           "trouver le résultat) et sert à mesurer la précision de l'IA.")
        hippo_input, txt_in = course_pmu["hippodrome"] if course_pmu else "", ""
    else:
        hippo_input = st.text_input("Hippodrome", value="Vincennes")
        txt_in = st.text_area("Collez les partants copiés depuis un site (avec les cotes), ou un cheval par ligne "
                              "(ex: 12 FAKIR D4 1a 2a 4.5)", height=200)

    def budget_pertes():
        if limite_pertes <= 0:
            return None
        histo, _ = stockage.lire(FEUILLE, tl.COLONNES_HISTORIQUE)
        return limite_pertes - max(tl.pertes_recentes(histo, pd.Timestamp.now()), 0)

    def conseil_pour(df):
        st.session_state["conseil"] = {"course": course_pmu["id"], "jour": jour, "profil": profil,
                                       **calculer_conseil_place(stockage, course_pmu, jour, df, profil,
                                                                capital, budget_pertes())}

    if source == PMU and course_pmu and st.button(
            "🎯 CONSEIL PLACÉ (gratuit, sans IA)", width="stretch",
            help="Règle confirmée sur des courses passées : compare les chances de placé (déduites des cotes "
                 "du Gagnant) aux cotes probables du Placé. Aucune requête Gemini."):
        st.session_state.pop("resultat", None)
        try:
            conseil_pour(partants_pmu(jour, course_pmu["reunion"], course_pmu["course"]))
        except pmu.PmuErreur as e:
            st.error(f"❌ {e}")

    if st.button("⚡ ANALYSER LA COURSE (IA)", width="stretch"):
        st.session_state.pop("resultat", None)
        st.session_state.pop("conseil", None)
        lignes_ignorees = []
        try:
            if source == PMU:
                df = partants_pmu(jour, course_pmu["reunion"], course_pmu["course"]) if course_pmu \
                    else pd.DataFrame()
            else:
                df, lignes_ignorees = tl.extraire_data_pro(txt_in)
        except pmu.PmuErreur as e:
            st.error(f"❌ {e}")
            df = pd.DataFrame()
        if lignes_ignorees:
            st.warning("⚠️ Lignes non reconnues (ignorées) :\n\n"
                       + "\n\n".join(f"- `{l}`" for l in lignes_ignorees))
        if df.empty:
            st.error("Choisissez une course du programme, ou collez des partants (ex: 12 NOM).")
        else:
            notes = []
            if course_pmu:
                conseil_pour(df)  # le conseil Placé ne dépend pas de l'IA : il s'affiche même si Gemini échoue
            terminee = bool(course_pmu and course_pmu["statut"] == "terminée")
            detectee = (course_pmu["discipline"] if course_pmu and course_pmu["discipline"] != "Non précisée"
                        else tl.detecter_discipline(df))
            if choix_discipline == AUTO:
                discipline = detectee or "Non précisée"
            else:
                discipline = choix_discipline
                if detectee and detectee != discipline:
                    notes.append(f"La musique des chevaux indique plutôt **{detectee}** "
                                 f"alors que vous avez choisi **{discipline}**.")
            partants_str = "\n".join(f"{row['FULL_ID']} ({row['Info']})" for _, row in df.iterrows())

            with st.spinner("🧪 Recherches, analyse de la course et calcul de la valeur..."):
                try:
                    recherches = lancer_recherches(hippo_input, discipline, partants_str,
                                                   recherche and not terminee, avec_presse and not terminee,
                                                   course_pmu["libelle"] if course_pmu else "")
                    contexte = recherches.get("contexte")
                    if isinstance(contexte, tl.GeminiErreur):
                        notes.append(f"Recherche Google indisponible ({contexte}) : analyse sans données du jour.")
                        contexte = None

                    compil, alertes_presse = None, []
                    if avec_presse and not terminee:
                        trouve = recherches["presse"]
                        if isinstance(trouve, tl.GeminiErreur):
                            notes.append(f"Pronostics de la presse indisponibles ({trouve}).")
                        else:
                            try:
                                compil = tl.compiler_pronostics(tl.lire_pronostics(trouve[0]), trouve[1], df)
                                alertes_presse = compil["alertes"]
                            except ValueError:
                                notes.append("Pronostics de la presse illisibles : ignorés.")

                    raw = analyser_course(partants_str, hippo_input, discipline, profil, contexte,
                                          tl.texte_consensus(compil), API_KEY)
                    res, alertes = tl.valider_reponse(tl.extraire_json(raw), df)
                    alertes += alertes_presse

                    budget = budget_pertes()
                    decision = tl.evaluer_pari(res["chevaux"], df, capital, profil, budget, confiance)

                    # Chaque analyse est enregistrée, jouée ou non, pour mesurer la précision
                    # préfixe « A » : l'identifiant reste du texte quand Google Sheets le relit
                    identifiant = "A" + datetime.now().strftime("%Y%m%d%H%M%S%f")
                    try:
                        ligne = mesure.ligne_analyse(
                            identifiant, datetime.now().strftime("%Y-%m-%d %H:%M"),
                            pmu.date_pmu(jour) if course_pmu else "", course_pmu["id"] if course_pmu else "",
                            hippo_input, discipline, profil, decision)
                        analyses, existe = stockage.lire(FEUILLE_ANALYSES, mesure.COLONNES_ANALYSES)
                        stockage.ecrire(FEUILLE_ANALYSES, mesure.ajouter_analyse(analyses, ligne), existe)
                    except Exception:
                        notes.append("Analyse non enregistrée : elle ne comptera pas dans la mesure de précision. "
                                     + (stockage.derniere_erreur or "Stockage indisponible."))

                    st.session_state["resultat"] = {
                        "res": res, "decision": decision, "alertes": alertes, "notes": notes, "presse": compil,
                        "hippo": hippo_input, "discipline": discipline, "profil": profil,
                        "course": course_pmu["id"] if course_pmu else "", "analyse": identifiant,
                        "confiance": confiance, "confiance_mesuree": confiance_mesuree,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "enregistre": False,
                    }
                except tl.GeminiErreur as e:
                    st.error(f"❌ {e}")
                except (ValueError, KeyError, TypeError):
                    st.error("Erreur d'analyse de la réponse Gemini. Réessayez l'envoi.")

    # Conseil Placé de la course affichée (sans IA)
    cp = st.session_state.get("conseil")
    if cp and course_pmu and source == PMU and cp["course"] == course_pmu["id"] and cp["jour"] == jour:
        st.markdown(conseil_place_html(cp["conseil"], cp["profil"]), unsafe_allow_html=True)
        if cp["note"]:
            st.caption(f"ℹ️ {cp['note']}")

    # Le résultat est gardé en mémoire : il reste affiché quand on clique sur « Enregistrer ».
    r = st.session_state.get("resultat")
    if r:
        res, decision = r["res"], r["decision"]
        pari = decision["pari"]

        # 1. LE VERDICT, en gros
        compil = r.get("presse")
        st.markdown(verdict_html(decision, r["profil"], compil), unsafe_allow_html=True)
        for alerte in r["alertes"]:
            st.warning(f"⚠️ {alerte}")
        for note in r["notes"]:
            st.caption(f"ℹ️ {note}")

        # 2. LE CLASSEMENT
        st.markdown("#### 🏁 Classement de l'IA")
        st.markdown(classement_html(res, decision, compil), unsafe_allow_html=True)
        st.caption(f"{r['discipline']} · {r['hippo']} · météo {res['m']} · distance {res['d']} · "
                   f"course jugée : {res['r']}")

        # 3. LES PRONOSTIQUEURS
        if compil is not None:
            st.markdown("#### 📰 Ce que disent les pronostiqueurs")
            if compil["sources"]:
                st.markdown(presse_html(compil), unsafe_allow_html=True)
                liens = " ".join(f'<a href="{escape(s["url"] or "#")}" target="_blank">{escape(s["nom"])}</a>'
                                 for s in compil["sources"])
                st.markdown(f'<div class="tm-sous tm-sources">Sources ({len(compil["sources"])}) : {liens}</div>',
                            unsafe_allow_html=True)
                st.caption("Points : 1er choix d'une source = 5 pts, 2e = 4 … 5e = 1. "
                           "Cet avis est transmis à l'IA, mais ne décide jamais seul d'un pari.")
            else:
                st.caption("Aucun pronostic vérifiable trouvé pour cette course.")
            if compil["ecartees"]:
                noms = ", ".join(compil["ecartees_noms"])
                if compil["nb_consultees"] == 0:
                    st.caption(f"{compil['ecartees']} source(s) écartée(s) ({noms}) : la recherche n'a renvoyé "
                               "aucune page vérifiable, impossible de confirmer qu'elles existent.")
                else:
                    st.caption(f"{compil['ecartees']} source(s) écartée(s) ({noms}) : introuvable(s) parmi les "
                               f"{compil['nb_consultees']} sites réellement consultés par la recherche "
                               "(risque d'invention).")

        # 4. LE DÉTAIL, pour qui veut comprendre
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
            part = (f"mesurée sur {precision['n']} courses" if r["confiance_mesuree"]
                    else f"valeur par défaut, mesurée à partir de {mesure.MINIMUM_COURSES} courses "
                         f"({precision.get('n', 0)} pour l'instant)")
            st.caption(f"Proba retenue = {r['confiance']:.0%} IA + {1 - r['confiance']:.0%} cotes ({part}). "
                       "Gain espéré = proba retenue × cote − 1. "
                       f"Règles du profil {r['profil']} : {tl.decrire_profil(r['profil'])}. "
                       "Les probabilités de l'IA sont des estimations, pas une garantie.")

        if decision["jouer"]:
            if r["enregistre"]:
                st.success("✅ Ticket enregistré dans l'historique.")
            elif st.button("💾 J'ai joué ce pari : enregistrer le ticket"):
                try:
                    histo, existe = stockage.lire(FEUILLE, tl.COLONNES_HISTORIQUE)
                    ligne = tl.ligne_historique(r["date"], r["hippo"], r["discipline"], r["profil"], pari,
                                                r["course"], r["analyse"])
                    stockage.ecrire(FEUILLE, pd.concat([histo, pd.DataFrame([ligne])], ignore_index=True), existe)
                    r["enregistre"] = True
                    st.rerun()
                except Exception:
                    st.error("Impossible d'enregistrer le ticket. "
                             + (stockage.derniere_erreur or "Stockage indisponible."))

with onglet_plan:
    st.caption("Toutes les courses françaises à venir sont passées au crible **gratuitement** (sans IA) avec la "
               "règle Placé ; les plus prometteuses sont retenues et le budget est réparti selon le profil.")
    UN_COUP, DUREE = "🎯 One shot : je joue ce budget une fois", "📈 Dans la durée (capital et protection)"
    mode = st.radio("Mode", [UN_COUP, DUREE], horizontal=True, label_visibility="collapsed",
                    help="One shot : le budget est joué une seule fois, sans lien avec un capital (vous acceptez de "
                         "le perdre). Dans la durée : les mises suivent votre capital et sa protection.")
    c1, c2 = st.columns([2, 1])
    budget_jour = c1.slider("Budget du jour (€)", 20, 100, 50, step=5)
    avec_joker = c2.toggle("🃏 Joker outsider", value=False,
                           help="10 % du budget sur le meilleur outsider (cote Gagnant ≥ 8) qui passe la règle "
                                "Placé. Non prouvé : très peu de données passées, résultats très variables.")
    if st.button("🔍 ANALYSER TOUTES LES COURSES DU JOUR (gratuit)", width="stretch"):
        barre = st.progress(0.0, text="Lecture du programme...")

        def avancement(k, n, c):
            barre.progress(k / max(n, 1), text=f"{c['id']} · {c['hippodrome']} ({k + 1}/{n})")
        try:
            conseils_jour, vus = plan.cribler(date.today(), datetime.now(tz=pmu.PARIS), lire_partants=partants_pmu,
                                              lire_cotes=cotes_place_pmu, programme=programme_pmu(date.today()),
                                              pause=0.2, progression=avancement)
            st.session_state["plan"] = {"conseils": conseils_jour, "vus": vus, "ia": {},
                                        "heure": datetime.now(tz=pmu.PARIS).strftime("%H:%M")}
        except pmu.PmuErreur as e:
            st.error(f"❌ {e}")
        barre.empty()

    pl = st.session_state.get("plan")
    if pl:
        conseils_jour = pl["conseils"]
        st.caption(f"Analyse de {pl['heure']} : {pl['vus']} courses à venir, "
                   f"{conseils_jour['course'].nunique() if not conseils_jour.empty else 0} avec un Placé intéressant.")
        if mode == UN_COUP:
            budget_principal = budget_jour * (1 - plan.PART_JOKER) if avec_joker else budget_jour
            sel, bilan_os = plan.one_shot(conseils_jour, budget_principal, profil)
            jok = plan.joker(conseils_jour, sel, budget_jour) if avec_joker and bilan_os["feu"] != "rouge" else None
            st.markdown(feu_html(bilan_os, budget_jour), unsafe_allow_html=True)
            if bilan_os["feu"] == "rouge":
                if not sel.empty:
                    st.caption("Paris écartés : " + ", ".join(f"{r['course']} n° {r['num']} {r['nom']}"
                                                              for _, r in sel.iterrows()))
                sel = sel.assign(mise=[0.0] * len(sel))
            else:
                st.markdown(plan_html(sel, jok, budget_jour, profil), unsafe_allow_html=True)
        else:
            budget_effectif = budget_jour * etat_capital["facteur"]
            if etat_capital["reduit"]:
                st.warning(f"🛡️ Protection active : budget ramené à {euros(budget_effectif)} "
                           f"(capital {etat_capital['baisse']:.0%} sous son plus haut).")
            sel, jok = plan.composer(conseils_jour, budget_effectif, profil, avec_joker, budget_pertes())
            st.markdown(plan_html(sel, jok, budget_jour, profil), unsafe_allow_html=True)
        retenues = ([r for _, r in sel.iterrows() if r["mise"] > 0] if not sel.empty else []) \
            + ([pd.Series(jok)] if jok else [])
        for r in retenues:
            if r["course"] in pl["ia"]:
                st.caption(f"🔬 {r['course']} n° {r['num']} : {pl['ia'][r['course']]}")

        b1, b2 = st.columns(2)
        if retenues and b1.button("🔄 Actualiser les cotes des courses retenues", width="stretch"):
            st.cache_data.clear()  # relit les cotes du PMU
            frais = conseils_jour[~conseils_jour["course"].isin([r["course"] for r in retenues])]
            nouveaux = []
            for r in retenues:
                try:
                    course = {"id": r["course"], "heure": r["heure"], "hippodrome": r["hippodrome"],
                              "discipline": r["discipline"], "libelle": r["libelle"],
                              "reunion": int(r["reunion"]), "course": int(r["numero"])}
                    nouveaux += plan.evaluer_course(course, partants_pmu(date.today(), course["reunion"], course["course"]),
                                                    cotes_place_pmu(date.today(), course["reunion"], course["course"]))
                except pmu.PmuErreur:
                    continue
            pl["conseils"] = pd.concat([frais, pd.DataFrame(nouveaux, columns=conseils_jour.columns)], ignore_index=True)
            pl["heure"] = datetime.now(tz=pmu.PARIS).strftime("%H:%M")
            st.rerun()
        if retenues and b2.button(f"🔬 Approfondir avec l'IA ({len(retenues)} requêtes Gemini)", width="stretch",
                                  help="Avis de l'IA sur chaque cheval retenu. Informatif : l'IA n'a pas prouvé "
                                       "qu'elle faisait mieux que les cotes, elle ne change pas le pari."):
            with st.spinner("Analyse par l'IA..."):
                for r in retenues:
                    try:
                        df_c = partants_pmu(date.today(), int(r["reunion"]), int(r["numero"]))
                        pl["ia"][r["course"]] = avis_ia(r, df_c, profil)
                    except tl.GeminiErreur as e:
                        pl["ia"][r["course"]] = f"IA indisponible ({e})"
                        break
                    except (pmu.PmuErreur, ValueError, KeyError, TypeError):
                        pl["ia"][r["course"]] = "analyse impossible"
            st.rerun()
        with st.expander("Toutes les courses avec un Placé intéressant"):
            if conseils_jour.empty:
                st.caption("Aucune.")
            else:
                st.dataframe(conseils_jour.drop(columns=["reunion", "numero", "libelle", "gain_regle"]),
                             hide_index=True, width="stretch", column_config={
                                 "proba_corrigee": st.column_config.NumberColumn("Chances placé", format="percent"),
                                 "valeur": st.column_config.NumberColumn("Valeur", format="percent")})

with onglet_histo:
    if message_sheets:
        st.warning(message_sheets)
    if stockage.derniere_erreur:
        st.error(f"❌ Google Sheets : {stockage.derniere_erreur}")
    if stockage.local:
        st.caption("📁 Données enregistrées dans des fichiers sur la machine qui fait tourner l'application. "
                   "Sur Streamlit Cloud, elles sont **perdues à chaque redémarrage** : configurez Google Sheets "
                   "(voir le README) pour les garder.")

    # 1. Récupérer les arrivées
    c1, c2 = st.columns([1, 1])
    avec_gemini = c2.checkbox("Aussi par recherche Gemini pour les courses collées",
                              help="1 requête Gemini par course, 5 au maximum par clic. Résultat non officiel.")
    if c1.button("🔄 Récupérer les arrivées", width="stretch"):
        with st.spinner("Recherche des arrivées..."):
            st.session_state["compte_rendu"] = recuperer_arrivees(stockage, avec_gemini)
        st.rerun()
    if st.session_state.get("compte_rendu"):
        st.info(st.session_state.pop("compte_rendu"))

    # 1 bis. Faire avancer la mesure avec des courses déjà courues
    if st.button("🧪 Tester l'IA sur 5 courses passées", width="stretch",
                 help="Analyse 5 courses françaises des 7 derniers jours, sans recherche internet (l'IA ne "
                      "peut pas trouver le résultat), puis les compare à l'arrivée officielle. "
                      "Coûte 5 requêtes Gemini."):
        with st.spinner("Analyse de courses passées (environ 1 minute)..."):
            st.session_state["compte_rendu_test"] = tester_courses_passees(stockage, profil, capital, confiance)
        st.rerun()
    if st.session_state.get("compte_rendu_test"):
        st.info(st.session_state.pop("compte_rendu_test"))

    # 1 ter. Suivi à blanc des conseils Placé
    st.markdown("#### 🎯 Conseils Placé — suivi à blanc")
    suivi, _ = stockage.lire(FEUILLE_SUIVI, place.COLONNES_SUIVI)
    bilan = place.stats_suivi(suivi, "confirmée")
    essai = place.stats_suivi(suivi, "corrigée")
    objectif = 100
    if bilan["n"] == 0:
        st.caption(f"Aucun conseil réglé pour l'instant ({bilan['en_attente']} en attente). Les conseils sont "
                   "relevés automatiquement avant chaque départ (voir le README), ou à la demande avec le bouton "
                   "« Conseil Placé » ; ils sont réglés par « Récupérer les arrivées ».")
    else:
        m = st.columns(4)
        m[0].metric("Conseils réglés", f"{bilan['n']} (+{bilan['en_attente']} en attente)")
        m[1].metric("Placés", f"{bilan['places']:.0%}")
        m[2].metric("Rendement (1 € par conseil)", f"{bilan['rendement'] * 100:+.1f} %")
        m[3].metric("Gain fictif", f"{bilan['gain']:+.2f} €")
        if bilan["n"] < objectif:
            st.caption(f"Objectif : {objectif} conseils réglés avant de miser pour de vrai "
                       f"({bilan['n']}/{objectif}). Sur 479 courses passées, la règle a donné environ +18 %.")
        elif bilan["rendement"] > 0:
            st.success(f"Sur {bilan['n']} conseils réels, le rendement reste positif. Vous pouvez envisager "
                       "de miser de petites sommes, en gardant la limite de pertes.")
        else:
            st.warning(f"Sur {bilan['n']} conseils réels, le rendement est négatif : la règle ne marche pas "
                       "(ou plus). Ne misez pas.")
    jokers = place.stats_suivi(suivi, "confirmée", outsiders=True)
    if jokers["n"]:
        st.caption(f"🃏 Outsiders (cote Gagnant ≥ 8) parmi les conseils : {jokers['n']} réglés, placés "
                   f"{jokers['places']:.0%}, rendement {jokers['rendement'] * 100:+.1f} %.")
    if essai["n"]:
        st.caption(f"🧪 Règle corrigée (en essai) : {essai['n']} conseils réglés, placés {essai['places']:.0%}, "
                   f"rendement {essai['rendement'] * 100:+.1f} % pour 1 € par conseil.")
    with st.expander(f"Détail des conseils ({len(suivi)})"):
        if suivi.empty:
            st.caption("Aucun conseil enregistré.")
        else:
            st.dataframe(suivi, hide_index=True, width="stretch")

    # 2. Précision de l'IA face aux cotes
    st.markdown("#### 📏 L'IA prévoit-elle mieux que les cotes ?")
    if precision["n"] == 0:
        st.caption("Pas encore de course analysée avec son résultat. Analysez des courses (même sans jouer), "
                   "puis cliquez sur « Récupérer les arrivées ».")
    else:
        n = precision["n"]
        mieux = precision["log_ia"] < precision["log_cotes"]
        if n < mesure.MINIMUM_COURSES:
            st.info(f"**{n} course(s) mesurée(s)** sur les {mesure.MINIMUM_COURSES} nécessaires pour conclure. "
                    f"Pour l'instant, {'l’IA fait mieux' if mieux else 'les cotes font mieux'} — trop tôt pour s'y fier.")
        elif mieux:
            st.success(f"Sur {n} courses, **l'IA prévoit mieux que les cotes**. Sa part dans la probabilité "
                       f"retenue est réglée à **{confiance:.0%}**.")
        else:
            st.warning(f"Sur {n} courses, **les cotes prévoient mieux que l'IA**. Sa part est réglée à "
                       f"**{confiance:.0%}** : l'application conseillera rarement de jouer, et c'est normal.")
        m = st.columns(3)
        m[0].metric("Favori gagnant · IA", f"{precision['favori_ia']:.0%}")
        m[1].metric("Favori gagnant · cotes", f"{precision['favori_cotes']:.0%}")
        m[2].metric("Part d'IA idéale", f"{precision['meilleur_poids']:.0%}")
        st.caption(f"Erreur moyenne (plus bas = mieux) — IA : {precision['log_ia']:.3f}, cotes : "
                   f"{precision['log_cotes']:.3f} (perte logarithmique) ; IA : {precision['brier_ia']:.3f}, "
                   f"cotes : {precision['brier_cotes']:.3f} (score de Brier). « Favori gagnant » = part des "
                   "courses gagnées par le cheval jugé le plus probable.")
    with st.expander(f"🗂️ Toutes les analyses ({len(analyses_enregistrees)})"):
        if analyses_enregistrees.empty:
            st.caption("Aucune analyse enregistrée.")
        else:
            st.dataframe(analyses_enregistrees.drop(columns=["partants"]), hide_index=True, width="stretch")

    # 3. Tickets joués
    st.markdown("#### 🎫 Tickets joués")
    histo, existe = stockage.lire(FEUILLE, tl.COLONNES_HISTORIQUE)
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
        st.caption("Les résultats se remplissent avec « Récupérer les arrivées ». "
                   "Vous pouvez aussi les corriger à la main, puis enregistrer.")
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
                stockage.ecrire(FEUILLE, modifie, existe)
                st.success("✅ Résultats enregistrés.")
            except Exception:
                st.error("Impossible d'enregistrer les résultats. " + (stockage.derniere_erreur or ""))

st.divider()
st.caption("Pari conseillé uniquement si la valeur est mesurable | Programme et arrivées PMU | "
           "Précision de l'IA mesurée")
