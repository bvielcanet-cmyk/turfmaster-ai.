import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import json
from html import escape

import pandas as pd
import streamlit as st

import carnet
import decision
import mesure
import pmu
import turf_logic as tl

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="TurfMaster : aide à la décision", page_icon="🚦", layout="wide")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; font-size: 16px !important; }
    [data-testid="stMetricLabel"] { color: #1a1a1a !important; font-weight: 700 !important; font-size: 13px !important; margin-bottom: -8px !important; }
    [data-testid="stMetric"] { background-color: #bdc3c7 !important; padding: 8px 10px !important; border-radius: 8px !important; border: 1px solid #7f8c8d !important; }
    .stButton button { background-color: #000000; color: white; border-radius: 12px; font-weight: bold; }
    .stButton button:hover, .stButton button:focus, .stButton button:active { background-color: #333333; color: white; }

    /* Verdict : lisible en thème clair comme sombre (couleurs semi-transparentes) */
    .tm-verdict { border-radius: 14px; padding: 18px 20px; margin: 8px 0 18px; border: 2px solid; }
    .tm-oui { border-color: #1e9e4a; background: rgba(30, 158, 74, .12); }
    .tm-non { border-color: #d9822b; background: rgba(217, 130, 43, .12); }
    .tm-titre { font-size: 1.4rem; font-weight: 800; letter-spacing: .02em; line-height: 1.2; }
    .tm-oui .tm-titre { color: #1e9e4a; }
    .tm-non .tm-titre { color: #d9822b; }
    .tm-carte { border: 2px solid #3b82f6; border-radius: 16px; padding: 12px; margin-bottom: 14px; }
    .tm-pari-jour { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin: 8px 0 4px;
                    font-size: 1.15rem; font-weight: 700; }
    .tm-pari-jour b { font-size: 2.3rem; white-space: nowrap; }
    .tm-ticket { border-style: dashed; }
    .tm-ticket .tm-pari-jour { margin-bottom: 0; }
    .tm-etape { padding: 10px 0; margin-top: 8px; border-top: 1px solid rgba(127, 127, 127, .3); }
    .tm-cheval-joue { font-size: 1.15rem; font-weight: 800; margin: 4px 0; }
    .tm-cheval-joue u { text-decoration: none; color: #3b82f6; }
    .tm-issue { border-radius: 10px; padding: 8px 10px; margin-top: 6px; }
    .tm-gagne { background: rgba(30, 158, 74, .13); }
    .tm-perd { background: rgba(220, 38, 38, .11); }
    .tm-quand { font-size: .9rem; }
    .tm-fiabilite { font-weight: 700; font-size: .95rem; margin-top: 2px; }
    .tm-texte-vert { color: #1e9e4a; }
    .tm-texte-orange { color: #d9822b; }
    .tm-mise { font-size: 1rem; }
    .tm-titre-arrivee { display: flex; justify-content: space-between; font-size: .8rem; opacity: .7; margin-top: 12px; }
    .tm-cheval { display: flex; align-items: center; gap: 8px; padding: 4px 0; }
    .tm-cheval .tm-nom { font-weight: 400; }
    .tm-plus { margin-top: 8px; font-size: .9rem; }
    .tm-plus summary { cursor: pointer; opacity: .7; }
    .tm-course { flex: 1; line-height: 1.3; }
    .tm-course small { display: block; opacity: .7; }
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
    .tm-tete { display: flex; align-items: baseline; gap: 8px; }
    .tm-rang { width: 1.4em; }
    .tm-num { font-weight: 800; min-width: 1.8em; text-align: center; background: rgba(127, 127, 127, .2); border-radius: 6px; }
    .tm-nom { font-weight: 700; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .tm-tag { font-size: .72rem; font-weight: 700; padding: 1px 6px; border-radius: 6px; white-space: nowrap; }
    .tm-tag-out { color: #d9822b; border: 1px solid #d9822b; }
    .tm-pct { font-weight: 800; font-size: 1.15rem; white-space: nowrap; }
    .tm-barre { position: relative; height: 8px; border-radius: 4px; background: rgba(127, 127, 127, .2); margin-top: 6px; }
    .tm-ia { height: 100%; border-radius: 4px; background: #3b82f6; }
    .tm-marche { position: absolute; top: -3px; width: 3px; height: 14px; background: currentColor; opacity: .75; border-radius: 2px; }
    .tm-sous { font-size: .8rem; opacity: .7; margin-top: 3px; }
    .tm-presse { background: #8b5cf6; }
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

FEUILLE = "TurfMaster"  # onglet du Google Sheet : carnet des paris joués
FEUILLE_ANALYSES = "Analyses"  # onglet où sont rangées toutes les analyses (mesure de précision)
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
def analyser_course(partants_str, hippo, discipline, contexte, presse, _api_key):
    """Analyse mise en cache 1 h : recoller la même course ne consomme pas de quota.
    Les erreurs (exceptions) ne sont jamais mises en cache."""
    return tl.analyser(_api_key, tl.construire_prompt(partants_str, hippo, discipline, contexte, presse))


def lancer_recherches(hippo, discipline, partants_str, avec_contexte, avec_presse, course=""):
    """Recherche du jour (météo, terrain) et pronostics publiés, en parallèle.
    Retourne {"contexte": texte ou GeminiErreur, "presse": (texte, sources) ou GeminiErreur}."""
    memoire = memoire_recherches()
    jour = pmu.aujourd_hui().strftime("%d/%m/%Y")
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
        self.illisibles = set()  # onglets dont la lecture a échoué : on refuse de les réécrire
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
            if type(e).__name__ != "WorksheetNotFound":  # onglet absent = normal au début
                self.illisibles.add(feuille)
                self.derniere_erreur = ("Fichier local illisible." if self.local else expliquer_erreur_sheets(e))
            return pd.DataFrame(columns=colonnes), False
        self.illisibles.discard(feuille)
        df = df.dropna(how="all")
        for col in colonnes:
            if col not in df.columns:
                df[col] = ""
        return mesure.normaliser(df[colonnes]), True

    def ecrire(self, feuille, df, existe):
        if feuille in self.illisibles:
            raise RuntimeError("lecture impossible : écriture refusée pour ne rien effacer")
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


def tester_courses_passees(stockage, nombre=5, jours=7):
    """Analyse `nombre` courses françaises déjà courues (jours précédents), sans recherche internet,
    et les enregistre avec leur gagnant officiel. Les cotes y sont celles de la clôture : cela compare
    l'IA aux parieurs, cela ne teste aucun pari jouable.
    Retourne un message de compte rendu."""
    analyses, existe = stockage.lire(FEUILLE_ANALYSES, mesure.COLONNES_ANALYSES)
    deja = {(mesure.texte_cellule(a["date_course"]).zfill(8), a["course"]) for _, a in analyses.iterrows()}
    candidates = []
    for k in range(1, jours + 1):
        jour = pmu.aujourd_hui() - pd.Timedelta(days=k)
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
            raw = analyser_course(partants_str, c["hippodrome"], c["discipline"], None, None, API_KEY)
            res, _ = tl.valider_reponse(tl.extraire_json(raw), df)
        except tl.GeminiErreur as e:
            arret = str(e)
            break
        except (pmu.PmuErreur, ValueError, KeyError, TypeError):
            continue
        ligne = mesure.ligne_analyse("T" + datetime.now().strftime("%Y%m%d%H%M%S%f"),
                                     heure_paris().strftime("%Y-%m-%d %H:%M"), pmu.date_pmu(jour), c["id"],
                                     c["hippodrome"], c["discipline"], tl.comparer_chances(res["chevaux"], df))
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
    """Cherche le gagnant des analyses en attente et règle les paris du carnet.
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

    paris, existe_p = stockage.lire(FEUILLE, carnet.COLONNES)
    regles = 0
    for i, t in paris[paris["resultat"] == carnet.EN_ATTENTE].iterrows():
        if not t["course"] or not t["date_course"]:
            continue  # ancien ticket sans date de course : à compléter à la main
        try:
            if t["pari"] in carnet.DOUBLES:
                regles += carnet.regler_double(paris, i, lambda c: arrivee_pmu(t["date_course"], c))
            else:
                regles += carnet.regler(paris, i, arrivee_pmu(t["date_course"], t["course"]))
        except (pmu.PmuErreur, ValueError) as e:
            erreurs.append(str(e))
    if regles:
        stockage.ecrire(FEUILLE, paris, existe_p)

    morceaux = [f"{trouves} arrivée(s) récupérée(s)", f"{regles} pari(s) réglé(s)"]
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


def classement_html(res, chances, compil=None):
    """Les 5 chevaux préférés de l'IA, avec une barre IA et un trait pour les cotes."""
    marche = {l["num"]: l["proba_marche"] for _, l in chances.iterrows()}
    top = res["chevaux"][:5]
    connus = [marche.get(c["num"]) for c in top]
    echelle = max([c["p"] for c in top] + [q for q in connus if not pd.isna(q)]) or 1
    lignes = []
    for rang, c, q in zip(["🥇", "🥈", "🥉", "4", "5"], top, connus):
        a_cote = not pd.isna(q)
        etiquette = '<span class="tm-tag tm-tag-out">🔥 OUTSIDER</span>' if c["out"] else ""
        trait = f'<div class="tm-marche" style="left:{q / echelle * 100:.1f}%"></div>' if a_cote else ""
        avis = avis_presse(c["num"], compil)
        sous = " · ".join(x for x in [f"cotes {pct(q)}" if a_cote else "pas de cote", f"📰 {avis}" if avis else ""] if x)
        lignes.append(
            f'<div class="tm-ligne"><div class="tm-tete"><span class="tm-rang">{rang}</span>'
            f'<span class="tm-num">{escape(c["num"])}</span><span class="tm-nom">{escape(c["nom"])}</span>{etiquette}'
            f'<span class="tm-pct">{pct(c["p"])}</span></div>'
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


def heure_paris():
    return datetime.now(tz=pmu.PARIS).replace(tzinfo=None)


def montant_texte(x):
    return (f"{x:.0f}" if abs(x - round(x)) < .05 else f"{x:.1f}0".replace(".", ",")) + "\u00a0€"


def feu_html(ordre, partie=False):
    """Une course en un coup d'œil : fiabilité, cheval, un seul pourcentage."""
    couleur = decision.feu(ordre)
    if couleur is None:
        return ('<div class="tm-verdict tm-neutre"><div class="tm-titre">⚪ PAS D\'ESTIMATION</div>'
                '<div class="tm-pourquoi">Il faut au moins 4 partants et la cote de chacun.</div></div>')
    f, favori = decision.FEUX[couleur], ordre.iloc[0]
    classe = {"vert": "tm-oui", "orange": "tm-non", "rouge": "tm-rouge"}[couleur]
    suite = "✋ <b>Ne pas jouer.</b> Aucun cheval ne se détache." if couleur == "rouge" and not partie else ""
    return f"""<div class="tm-verdict {classe}">
<div class="tm-titre">{f['emoji']} {f['titre']}</div>
<div class="tm-pari-jour"><span>🏅 n° {escape(favori['num'])} {escape(favori['nom'])} placé</span>
<b>{pct(decision.chances_favori(ordre)[1])}</b></div>
<div class="tm-mise">{suite}</div>
</div>"""


def arrivee_html(chevaux):
    """L'arrivée estimée : un cheval par ligne, un seul pourcentage (être placé)."""
    medailles = {1: "🥇", 2: "🥈", 3: "🥉"}
    return '<div class="tm-arrivee">' + "".join(
        f'<div class="tm-cheval"><span class="tm-rang">{medailles.get(o["rang"], o["rang"])}</span>'
        f'<span class="tm-num">{escape(str(o["num"]))}</span><span class="tm-nom">{escape(str(o["nom"]))}</span>'
        f'<b>{pct(o["place"])}</b></div>' for o in chevaux) + "</div>"


def pronostics_html(liste):
    return "".join(
        f'<div class="tm-cheval"><span class="tm-nom">{escape(x["pari"])} '
        f'<small>{escape(x["chevaux"])}</small></span><b>{pct(x["chance"])}</b></div>' for x in liste)


def ticket_html(t, maintenant):
    """Le ticket du one-shot : quoi jouer, quand, et les deux seules issues."""
    mode, etapes = decision.MODES[t["cle"]], []
    pari = "PLACÉ" if mode["pari"] == "PLACE" else "GAGNANT"
    for k, e in enumerate(t["etapes"]):
        x, f = e["course"], decision.FEUX[e["course"]["feu"]]
        dans = decision.minutes_avant(x["heure"], maintenant)
        quand = f" · dans {dans} min" if 0 <= dans < 60 else ""
        if k == 0:
            mise = f'💶 Mets <b>{montant_texte(t["montant"])}</b> en Simple {pari.capitalize()}'
        else:
            combien = f' (environ {montant_texte(e["mise"])})' if e["mise"] else ""
            mise = f'🔁 Si le 1er passe, <b>rejoue tout ce qu\'il a rapporté</b>{combien}'
        numero = f"{k + 1}. " if len(t["etapes"]) > 1 else ""
        etapes.append(
            f'<div class="tm-etape"><div class="tm-quand">{numero}<b>{escape(x["heure"])}</b> '
            f'{escape(x["hippodrome"])} · {escape(x["course"])}{quand}</div>'
            f'<div class="tm-fiabilite tm-texte-{x["feu"]}">{f["emoji"]} {f["titre"]}</div>'
            f'<div class="tm-cheval-joue">🐎 n° {escape(x["num"])} {escape(x["nom"])} <u>{pari}</u></div>'
            f'<div class="tm-mise">{mise}</div></div>')
    tout = "les deux passent" if len(etapes) > 1 else "ça passe"
    return (f'<div class="tm-carte tm-ticket"><div class="tm-pari-jour"><span>🎟️ {mode["nom"]}</span>'
            f'<b>{pct(t["chance"])}</b></div><div class="tm-sous">de chances que ça passe</div>'
            f'{"".join(etapes)}'
            f'<div class="tm-issue tm-gagne">🎉 Si {tout} : tu gagnes environ <b>+{montant_texte(t["gain"])}</b></div>'
            f'<div class="tm-issue tm-perd">💸 Sinon : tu perds <b>tes {montant_texte(t["montant"])}</b></div></div>')


def jour_html(lignes):
    """Les autres courses : une ligne chacune."""
    html = []
    for x in lignes:
        detail = "ne pas jouer" if x["feu"] == "rouge" else f'{escape(x["favori"])} placé'
        html.append(
            f'<div class="tm-ligne tm-tete"><span>{decision.FEUX[x["feu"]]["emoji"]}</span>'
            f'<span class="tm-course"><b>{escape(x["heure"])}</b> {escape(x["hippodrome"])} · {escape(x["course"])}'
            f'<small>{detail}</small></span><span class="tm-pct">{pct(x["place"])}</span></div>')
    return "".join(html)


def risque_html(r):
    cout = (f"≈ {euros(r['cout_moyen'])}" if r["cout_moyen"] is not None else "🤷 inconnu")
    note = "perdus en moyenne" if r["cout_moyen"] is not None else "calcul peu fiable ici, comptez perdre"
    return f"""<div class="tm-chiffres">
<div><span>💸 Risque de perdre {euros(r['perte'])}</span><b>{pct(r['risque'])}</b><small>soit {r['risque'] * 10:.0f} fois sur 10 environ</small></div>
<div><span>🎉 Si ça passe</span><b>+{euros(r['gain'])}</b><small>à la cote du moment, qui bougera</small></div>
<div><span>🧾 Coût moyen du pari</span><b>{cout}</b><small>{note}</small></div>
</div>"""


# --- 3. INTERFACE ---
st.title("🚦 TurfMaster")
st.markdown("**Un one-shot pour s'amuser, sur une ou deux courses**")
st.caption("🎲 Aucun pari testé n'est rentable. Ne mise que ce que tu acceptes de perdre.")

with st.sidebar:
    budget_semaine = st.number_input("💶 Mon budget maximum sur 7 jours (€)", value=50, min_value=0,
                                     help="Tout ce qui est misé compte : un gain n'agrandit pas le budget.")
    st.divider()
    choix_discipline = st.selectbox("Discipline", [AUTO] + tl.DISCIPLINES)
    recherche = st.toggle("🔎 Recherche Google (météo, terrain, distance)", value=True,
                          help="Pour l'analyse IA. Faite une fois par hippodrome et par jour, puis réutilisée.")
    avec_presse = st.toggle("📰 Pronostics de la presse", value=True,
                            help="Pour l'analyse IA. Seules les sources réellement trouvées sont gardées.")
    st.caption("🆘 Le jeu devient pesant ? Joueurs Info Service : **09 74 75 13 13** (appel non surtaxé).")

conn, message_sheets = connexion_sheets()
stockage = Stockage(conn)
analyses_enregistrees, _ = stockage.lire(FEUILLE_ANALYSES, mesure.COLONNES_ANALYSES)
paris_notes, paris_existe = stockage.lire(FEUILLE, carnet.COLONNES)
deja_mise = carnet.mise_semaine(paris_notes, pd.Timestamp(heure_paris()))
paris_du_jour = carnet.nombre_du_jour(paris_notes, pmu.aujourd_hui())
with st.sidebar:
    if deja_mise >= budget_semaine and deja_mise > 0:
        st.error(f"🛑 Budget atteint : {euros(deja_mise)} misés sur 7 jours. On s'arrête là.")
    else:
        st.caption(f"Déjà misé sur 7 jours : **{euros(deja_mise)}** sur {euros(budget_semaine)}.")

# La clé garde l'onglet ouvert quand la page se recharge (après un clic sur un bouton)
onglet_jour, onglet_course, onglet_carnet = st.tabs(["🎯 One-shot", "🏇 La course", "📒 Mon carnet"],
                                                    key="onglet")

with onglet_course:
    PMU, COLLE = "📅 Programme PMU", "📋 Copier-coller"
    source = st.radio("Partants", [PMU, COLLE], horizontal=True, label_visibility="collapsed")
    course_pmu, jour, df, lignes_ignorees = None, pmu.aujourd_hui(), pd.DataFrame(), []
    if source == PMU:
        jour = st.date_input("Jour", value=jour, format="DD/MM/YYYY")
        try:
            courses = programme_pmu(jour)
            if courses:
                a_venir = next((i for i, c in enumerate(courses)
                                if c["statut"] == "à venir" and not pmu.depart_passe(c, jour)), 0)
                course_pmu = st.selectbox("Course", courses, index=a_venir, format_func=pmu.libelle_course)
                df = partants_pmu(jour, course_pmu["reunion"], course_pmu["course"])
        except pmu.PmuErreur as e:
            st.error(f"❌ {e}")
        hippo_input, txt_in = course_pmu["hippodrome"] if course_pmu else "", ""
    else:
        hippo_input = st.text_input("Hippodrome", value="Vincennes")
        txt_in = st.text_area("Colle les partants copiés depuis un site (avec les cotes), ou un cheval par ligne "
                              "(ex: 12 FAKIR D4 1a 2a 4.5)", height=200)
        if txt_in.strip():
            df, lignes_ignorees = tl.extraire_data_pro(txt_in)
    if lignes_ignorees:
        st.warning("⚠️ Lignes non reconnues (ignorées) :\n\n" + "\n\n".join(f"- `{l}`" for l in lignes_ignorees))

    terminee = bool(course_pmu and (course_pmu["statut"] != "à venir" or pmu.depart_passe(course_pmu, jour)))
    cle_course = (jour, course_pmu["id"]) if course_pmu else (source, txt_in)
    ordre = decision.ordre_estime(df) if not df.empty else pd.DataFrame()

    if not df.empty:
        if terminee:
            st.caption("⏱️ Course déjà partie : ces cotes sont celles de la clôture, inconnues au moment de parier.")
        offerts = course_pmu.get("paris") if course_pmu else None
        st.markdown(feu_html(ordre, terminee), unsafe_allow_html=True)

    if not ordre.empty:
        st.markdown('<div class="tm-titre-arrivee"><span>🏁 Arrivée estimée</span><span>chances d\'être placé</span></div>'
                    + arrivee_html(decision.chances_affichees(ordre).head(5).to_dict("records")), unsafe_allow_html=True)
        with st.expander("📊 Paris au-dessus de 30 %"):
            liste = decision.pronostics(ordre, offerts)
            if liste:
                st.markdown(pronostics_html(liste), unsafe_allow_html=True)
            else:
                st.caption("Aucun sur cette course.")
            if not offerts:
                st.caption("Course collée ou paris inconnus : seuls les paris Simples sont calculés.")
        with st.expander("🎲 Si je parie, qu'est-ce que je risque ?"):
            c1, c2, c3 = st.columns(3)
            type_pari = c1.selectbox("Pari", [decision.GAGNANT, decision.PLACE], index=None, placeholder="Choisir")
            noms = dict(zip(ordre["num"], ordre["nom"]))
            num = c2.selectbox("Mon cheval", list(noms), index=None, placeholder="Choisir",
                               format_func=lambda n: f"n° {n} {noms.get(n, '')}")
            mise = c3.number_input("Ma mise (€)", value=0.0, min_value=0.0, step=1.0)
            if type_pari and num and mise > 0:
                vu = decision.chances_affichees(ordre)
                choisi, cote = vu[vu["num"] == num].iloc[0], None
                if type_pari == decision.GAGNANT:
                    chance, cote = choisi["victoire"], float(choisi["cote"])
                else:
                    chance = choisi["place"]
                    if course_pmu:
                        try:
                            fourchette = cotes_place_pmu(jour, course_pmu["reunion"], course_pmu["course"]).get(num)
                            cote = fourchette[0] if fourchette else None
                        except pmu.PmuErreur:
                            cote = None
                if cote:
                    st.markdown(risque_html(decision.risque_pari(chance, cote, mise)), unsafe_allow_html=True)
                    if type_pari == decision.PLACE:
                        st.caption("🏅 Au Placé, ce calcul est souvent trop optimiste : sur les courses testées, "
                                   "jouer le favori placé a perdu en moyenne 11 % de la mise.")
                else:
                    st.caption(f"💸 Environ {pct(1 - chance)} de risque de perdre {euros(mise)}. "
                               "Cote du Placé inconnue : gain possible non chiffrable.")
                if deja_mise + mise > budget_semaine:
                    st.warning(f"🛑 Avec ce pari, tu dépasses ton budget de {euros(budget_semaine)} sur 7 jours.")
                if course_pmu and st.button("📒 J'ai joué ce pari : le noter dans mon carnet"):
                    try:
                        nouveau = carnet.ligne(heure_paris().strftime("%Y-%m-%d %H:%M"), pmu.date_pmu(jour),
                                               course_pmu["id"], hippo_input, course_pmu["discipline"],
                                               type_pari, num, cote or 0.0, mise)
                        stockage.ecrire(FEUILLE, pd.concat([paris_notes, pd.DataFrame([nouveau])], ignore_index=True),
                                        paris_existe)
                        st.session_state["pari_note"] = True
                        st.rerun()
                    except Exception:
                        st.error("Impossible de noter ce pari. " + (stockage.derniere_erreur or ""))
        if st.session_state.pop("pari_note", False):
            st.success("📒 Pari noté dans ton carnet.")

        with st.expander("🃏 Et les autres types de paris ?"):
            st.markdown(decision.AUTRES_PARIS)

    if st.button("🤖 DEMANDER L'AVIS DE L'IA ET DE LA PRESSE", width="stretch",
                 help="Jusqu'à 3 requêtes Gemini. Un avis en plus : l'IA n'a pas montré qu'elle fait mieux que les cotes."):
        st.session_state.pop("resultat", None)
        if df.empty:
            st.error("Choisis une course du programme, ou colle des partants (ex: 12 NOM).")
        else:
            notes = []
            detectee = (course_pmu["discipline"] if course_pmu and course_pmu["discipline"] != "Non précisée"
                        else tl.detecter_discipline(df))
            if choix_discipline == AUTO:
                discipline = detectee or "Non précisée"
            else:
                discipline = choix_discipline
                if detectee and detectee != discipline:
                    notes.append(f"La musique des chevaux indique plutôt **{detectee}** "
                                 f"alors que tu as choisi **{discipline}**.")
            partants_str = "\n".join(f"{row['FULL_ID']} ({row['Info']})" for _, row in df.iterrows())

            with st.spinner("🤖 Recherches et analyse de la course..."):
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

                    raw = analyser_course(partants_str, hippo_input, discipline, contexte,
                                          tl.texte_consensus(compil), API_KEY)
                    res, alertes = tl.valider_reponse(tl.extraire_json(raw), df)
                    alertes += alertes_presse
                    chances = tl.comparer_chances(res["chevaux"], df)

                    try:
                        # préfixe « A » : l'identifiant reste du texte quand Google Sheets le relit
                        ligne = mesure.ligne_analyse(
                            "A" + datetime.now().strftime("%Y%m%d%H%M%S%f"), heure_paris().strftime("%Y-%m-%d %H:%M"),
                            pmu.date_pmu(jour) if course_pmu else "", course_pmu["id"] if course_pmu else "",
                            hippo_input, discipline, chances)
                        analyses, existe = stockage.lire(FEUILLE_ANALYSES, mesure.COLONNES_ANALYSES)
                        stockage.ecrire(FEUILLE_ANALYSES, mesure.ajouter_analyse(analyses, ligne), existe)
                    except Exception:
                        notes.append("Analyse non enregistrée : elle ne comptera pas dans la mesure de précision. "
                                     + (stockage.derniere_erreur or "Stockage indisponible."))

                    st.session_state["resultat"] = {
                        "cle": cle_course, "res": res, "chances": chances, "alertes": alertes, "notes": notes,
                        "presse": compil, "hippo": hippo_input, "discipline": discipline,
                    }
                except tl.GeminiErreur as e:
                    st.error(f"❌ {e}")
                except (ValueError, KeyError, TypeError):
                    st.error("Erreur d'analyse de la réponse Gemini. Réessayez l'envoi.")

    r = st.session_state.get("resultat")
    if r and r["cle"] == cle_course:  # jamais le résultat d'une autre course
        res, compil = r["res"], r["presse"]
        for alerte in r["alertes"]:
            st.warning(f"⚠️ {alerte}")
        for note in r["notes"]:
            st.caption(f"ℹ️ {note}")
        st.markdown("#### 🤖 L'avis de l'IA")
        st.markdown(classement_html(res, r["chances"], compil), unsafe_allow_html=True)
        st.caption(f"{r['discipline']} · {r['hippo']} · météo {res['m']} · distance {res['d']} · "
                   "un avis en plus, qui n'a pas montré qu'il fait mieux que les cotes.")
        if compil is not None:
            st.markdown("#### 📰 Ce que disent les pronostiqueurs")
            if compil["sources"]:
                st.markdown(presse_html(compil), unsafe_allow_html=True)
                liens = " ".join(f'<a href="{escape(s["url"] or "#")}" target="_blank">{escape(s["nom"])}</a>'
                                 for s in compil["sources"])
                st.markdown(f'<div class="tm-sous tm-sources">Sources ({len(compil["sources"])}) : {liens}</div>',
                            unsafe_allow_html=True)
                st.caption("Points : 1er choix d'une source = 5 pts, 2e = 4 … 5e = 1.")
            else:
                st.caption("Aucun pronostic vérifiable trouvé pour cette course.")
            if compil["ecartees"]:
                noms_ecartes = ", ".join(compil["ecartees_noms"])
                if compil["nb_consultees"] == 0:
                    st.caption(f"{compil['ecartees']} source(s) écartée(s) ({noms_ecartes}) : la recherche n'a renvoyé "
                               "aucune page vérifiable, impossible de confirmer qu'elles existent.")
                else:
                    st.caption(f"{compil['ecartees']} source(s) écartée(s) ({noms_ecartes}) : introuvable(s) parmi les "
                               f"{compil['nb_consultees']} sites réellement consultés par la recherche "
                               "(risque d'invention).")

with onglet_jour:
    montant = st.radio("💶 Je mets", decision.MONTANTS, horizontal=True, format_func=montant_texte)
    reste = max(budget_semaine - deja_mise, 0)
    st.caption(f"Budget des 7 jours : il reste **{montant_texte(reste)}** sur {montant_texte(budget_semaine)}.")

    if st.session_state.pop("oneshot_note", False):
        st.success("📒 One-shot noté. Bonne course !")
    if paris_du_jour:
        st.markdown("### 🏁 C'est joué pour aujourd'hui")
        st.caption("Un one-shot, c'est une fois. Le résultat t'attend dans 📒 Mon carnet, "
                   "avec « Récupérer les arrivées ».")
    elif montant > reste:
        st.warning(f"🛑 {montant_texte(montant)} dépasse ce qu'il reste de ton budget des 7 jours. "
                   "Choisis moins, ou garde-le pour une autre fois.")
    else:
        feux = st.session_state.get("feux")
        if st.button("🔄 ACTUALISER LES COURSES" if feux else "🔎 TROUVER MON ONE-SHOT", width="stretch",
                     help="Gratuit. Lit toutes les courses françaises encore à venir (environ 30 secondes)."):
            try:
                with st.spinner("🐎 Je regarde toutes les courses (environ 30 secondes)..."):
                    partants_pmu.clear()
                    cotes_place_pmu.clear()
                    feux = {"jour": pmu.aujourd_hui(), "heure": heure_paris().strftime("%H:%M"),
                            "lignes": decision.cribler(pmu.aujourd_hui(), datetime.now(tz=pmu.PARIS),
                                                       programme_pmu(pmu.aujourd_hui()), partants_pmu)}
                    st.session_state["feux"] = feux
                    st.rerun()
            except pmu.PmuErreur as e:
                st.error(f"❌ {e}")

        if feux:
            # une liste gardée à l'écran ne doit pas conseiller une course déjà partie
            restantes = [x for x in feux["lignes"] if not pmu.depart_passe(x, feux["jour"])]
            possibles = decision.jouables(restantes, "tranquille")
            if not possibles:
                st.markdown("✋ **Ne pas jouer** : aucune course assez fiable parmi celles qui restent.")
            else:
                noms_courses = {x["course"]: f"{x['heure']} {x['hippodrome']} · {x['course']}" for x in possibles}
                cle_voulue = st.session_state.get("course_voulue")
                if cle_voulue and cle_voulue not in noms_courses:
                    del st.session_state["course_voulue"]  # elle est partie ou devenue trop ouverte
                zone_modes, zone_ticket = st.container(), st.container()
                voulue = st.selectbox(
                    "🐎 Ou je choisis ma course", list(noms_courses), index=None, key="course_voulue",
                    placeholder="La meilleure est choisie pour toi", format_func=lambda c: noms_courses.get(c, c))

                def cote_de(x, mode):
                    if mode["pari"] == "GAGNANT":
                        return x["cote"]
                    try:
                        fourchette = cotes_place_pmu(feux["jour"], x["reunion"], x["numero"]).get(x["num"])
                    except pmu.PmuErreur:
                        return None
                    return fourchette[0] if fourchette else None

                tickets = {}
                for cle, mode in decision.MODES.items():
                    choisies = decision.choisir_courses(restantes, cle, voulue)
                    if choisies:
                        tickets[cle] = decision.ticket(cle, choisies, montant, [cote_de(x, mode) for x in choisies])

                if not tickets:
                    st.markdown("✋ **Ne pas jouer** cette course : le pari n'y est pas proposé.")
                else:
                    with zone_modes:
                        if st.session_state.get("facon") not in tickets:
                            st.session_state.pop("facon", None)
                        facon = st.radio(
                            "🎲 Je joue comment ?", list(tickets), key="facon",
                            format_func=lambda c: f"{decision.MODES[c]['nom']} : {decision.MODES[c]['quoi']}",
                            captions=[f"{pct(t['chance'])} de chances · +{montant_texte(t['gain'])} environ"
                                      for t in tickets.values()])
                        if len(tickets) < len(decision.MODES):
                            st.caption("Pas de deuxième course assez fiable pour enchaîner.")
                    with zone_ticket:
                        t, mode = tickets[facon], decision.MODES[facon]
                        maintenant = heure_paris()
                        st.markdown(ticket_html(t, maintenant), unsafe_allow_html=True)
                        if t["gain"] < decision.PETIT_GAIN * montant:
                            st.warning(f"🤏 **Très petit gain** : +{montant_texte(t['gain'])} pour "
                                       f"{montant_texte(montant)} risqués. Ça n'en vaut sans doute pas la peine : "
                                       "choisis une autre course, ou passe.")
                        depart = t["etapes"][0]["course"]["heure"]
                        if decision.minutes_avant(depart, maintenant) > decision.ACTUALISER_AVANT:
                            rappel = (pd.Timestamp(f"{feux['jour']} {depart}") - pd.Timedelta(minutes=10)).strftime("%H:%M")
                            st.info(f"⏰ **Provisoire.** Reviens vers **{rappel}** et actualise avant de jouer : "
                                    "c'est là que l'estimation est la plus juste.")
                        st.caption(f"Cotes de {feux['heure']}. Pour s'amuser, pas pour gagner à la longue.")
                        if st.button("📒 C'est joué, note-le", width="stretch"):
                            try:
                                etapes = [e["course"] for e in t["etapes"]]
                                nouveau = carnet.ligne(
                                    heure_paris().strftime("%Y-%m-%d %H:%M"), pmu.date_pmu(feux["jour"]),
                                    carnet.SUITE.join(x["course"] for x in etapes),
                                    carnet.SUITE.join(x["hippodrome"] for x in etapes), "", mode["carnet"],
                                    carnet.SUITE.join(x["num"] for x in etapes), t["etapes"][0]["cote"] or 0.0,
                                    montant)
                                stockage.ecrire(FEUILLE, pd.concat([paris_notes, pd.DataFrame([nouveau])],
                                                                   ignore_index=True), paris_existe)
                                st.session_state["oneshot_note"] = True
                                st.rerun()
                            except Exception:
                                st.error("Impossible de noter ce pari. " + (stockage.derniere_erreur or ""))
                        with st.expander("🏁 Arrivée estimée"):
                            for e in t["etapes"]:
                                x = e["course"]
                                st.markdown(
                                    f'<div class="tm-titre-arrivee"><span>{escape(x["heure"])} '
                                    f'{escape(x["hippodrome"])}</span><span>chances d\'être placé</span></div>'
                                    + arrivee_html(x["arrivee"][:5]), unsafe_allow_html=True)
                                autres_paris = [p for p in x["pronostics"]
                                                if p["code"] not in ("SIMPLE_PLACE", "SIMPLE_GAGNANT")]
                                if autres_paris:
                                    st.caption("Autres paris au-dessus de 30 %")
                                    st.markdown(pronostics_html(autres_paris), unsafe_allow_html=True)
            if restantes:
                with st.expander(f"📋 Voir les {len(restantes)} courses à venir"):
                    st.caption("  \n".join(f"{f['emoji']} **{f['titre']}** ({f['sur10']} favoris placés sur 10)"
                                           for f in decision.FEUX.values()))
                    st.caption("À droite : chances du favori d'être placé.")
                    st.markdown(jour_html(restantes), unsafe_allow_html=True)

with onglet_carnet:
    if message_sheets:
        st.warning(message_sheets)
    if stockage.derniere_erreur:
        st.error(f"❌ Stockage : {stockage.derniere_erreur}")
    if stockage.local:
        st.caption("📁 Données enregistrées dans des fichiers sur la machine qui fait tourner l'application. "
                   "Sur Streamlit Cloud, elles sont **perdues à chaque redémarrage** : configurez Google Sheets "
                   "(voir le README) pour les garder.")

    c1, c2 = st.columns([1, 1])
    avec_gemini = c2.checkbox("Aussi par recherche Gemini pour les courses collées",
                              help="1 requête Gemini par course, 5 au maximum par clic. Résultat non officiel.")
    if c1.button("🔄 Récupérer les arrivées", width="stretch"):
        with st.spinner("Recherche des arrivées..."):
            try:
                st.session_state["compte_rendu"] = recuperer_arrivees(stockage, avec_gemini)
            except Exception:
                st.session_state["compte_rendu"] = "Enregistrement impossible : les résultats n'ont pas tous été sauvegardés."
        st.rerun()
    if st.session_state.get("compte_rendu"):
        st.info(st.session_state.pop("compte_rendu"))

    st.markdown("#### 📒 Mes paris, pour de vrai")
    b = carnet.bilan(paris_notes)
    m = st.columns(4)
    m[0].metric("Paris réglés", f"{b['n']} (+{b['attente']} en attente)")
    m[1].metric("Gagnés", str(b["gagnes"]))
    m[2].metric("Misé", euros(b["mise"]))
    m[3].metric("Résultat net", ("+" if b["net"] > 0 else "") + euros(b["net"]))
    if paris_notes.empty:
        st.caption("Aucun pari noté.")
    else:
        modifie = st.data_editor(
            paris_notes, hide_index=True, width="stretch",
            column_order=["date", "course", "hippodrome", "pari", "chevaux", "mise", "resultat", "gain_reel"],
            disabled=[c for c in carnet.COLONNES if c not in ("resultat", "gain_reel")],
            column_config={
                "resultat": st.column_config.SelectboxColumn("Résultat", options=carnet.RESULTATS),
                "gain_reel": st.column_config.NumberColumn("Rapporté (€)", min_value=0.0, format="%.2f"),
                "mise": st.column_config.NumberColumn("Mise (€)", format="%.2f"),
            },
        )
        if st.button("💾 Enregistrer mes corrections"):
            try:
                stockage.ecrire(FEUILLE, modifie, paris_existe)
                st.success("✅ Corrections enregistrées.")
            except Exception:
                st.error("Impossible d'enregistrer. " + (stockage.derniere_erreur or ""))

    st.markdown("#### 📏 L'IA prévoit-elle mieux que les cotes ?")
    precision = mesure.scores(analyses_enregistrees)
    if precision["n"] == 0:
        st.caption("Pas encore de course analysée avec son résultat.")
    else:
        n = precision["n"]
        mieux = "l'IA" if precision["log_ia"] < precision["log_cotes"] else "les cotes"
        suite = ("trop tôt pour conclure" if n < mesure.MINIMUM_COURSES
                 else "mieux prévoir ne veut pas dire gagner de l'argent")
        st.info(f"**{n} course(s) mesurée(s)** · en tête pour l'instant : {mieux} ({suite}).")
        st.caption(f"Erreur moyenne (plus bas = mieux) : IA {precision['log_ia']:.3f}, cotes "
                   f"{precision['log_cotes']:.3f}. Favori gagnant : IA {pct(precision['favori_ia'])}, cotes "
                   f"{pct(precision['favori_cotes'])}.")
    if st.button("🧪 Tester l'IA sur 5 courses passées", width="stretch",
                 help="5 requêtes Gemini. Compare l'IA aux cotes de clôture : cela ne teste aucun pari jouable."):
        with st.spinner("Analyse de courses passées (environ 1 minute)..."):
            try:
                st.session_state["compte_rendu_test"] = tester_courses_passees(stockage)
            except Exception:
                st.session_state["compte_rendu_test"] = "Enregistrement impossible : test non sauvegardé."
        st.rerun()
    if st.session_state.get("compte_rendu_test"):
        st.info(st.session_state.pop("compte_rendu_test"))

st.divider()
st.caption("🎯 Un one-shot, une fois · 🚦 le feu note l'estimation, pas le gain")
