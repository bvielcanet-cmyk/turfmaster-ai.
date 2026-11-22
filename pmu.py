"""Données du PMU : programme du jour, partants avec cotes, arrivées et rapports.

Source : les données publiques qu'affiche le site du PMU (online.turfinfo.api.pmu.fr).
Ce n'est pas une interface officiellement ouverte au public : elle peut changer sans
prévenir. L'application l'utilise avec modération (mise en mémoire) et garde le
copier-coller en solution de secours.
"""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests

BASE = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme"
PARIS = ZoneInfo("Europe/Paris")

DISCIPLINES = {"ATTELE": "Trot", "MONTE": "Trot", "PLAT": "Plat",
               "STEEPLECHASE": "Obstacles", "HAIE": "Obstacles", "CROSS": "Obstacles"}
FERRURES = {"DEFERRE_ANTERIEURS_POSTERIEURS": "D4", "DEFERRE_ANTERIEURS": "DA", "DEFERRE_POSTERIEURS": "DP"}
SEXES = {"HONGRES": "H", "FEMELLES": "F", "MALES": "M"}
STATUTS = {"ARRIVEE_DEFINITIVE_COMPLETE": "terminée", "ARRIVEE_DEFINITIVE": "terminée",
           "ARRIVEE_PROVISOIRE": "arrivée provisoire", "COURSE_ANNULEE": "annulée"}


class PmuErreur(Exception):
    """Erreur affichable telle quelle."""


def _get(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "TurfMaster (usage personnel)"})
    except requests.RequestException:
        raise PmuErreur("Site du PMU injoignable. Utilisez le copier-coller.")
    if r.status_code == 404:
        raise PmuErreur("Course ou programme introuvable au PMU.")
    if r.status_code != 200:
        raise PmuErreur(f"Le PMU a renvoyé une erreur (code {r.status_code}). Utilisez le copier-coller.")
    try:
        return r.json()
    except ValueError:
        raise PmuErreur("Réponse du PMU illisible. Utilisez le copier-coller.")


def aujourd_hui():
    """Date du jour à Paris (le serveur Streamlit est en UTC)."""
    return datetime.now(tz=PARIS).date()


def date_pmu(jour):
    """date -> « 21112026 »."""
    return jour.strftime("%d%m%Y")


def _heure(ms):
    return datetime.fromtimestamp(ms / 1000, tz=PARIS).strftime("%H:%M") if ms else "?"


# --- Programme -----------------------------------------------------------

def lire_programme(data):
    """Liste des courses du programme : une entrée par course, dans l'ordre des réunions."""
    courses = []
    for r in data.get("programme", {}).get("reunions", []):
        hippo = r.get("hippodrome", {}).get("libelleCourt", "?")
        pays = r.get("pays", {}).get("code", "")
        for c in r.get("courses", []):
            arrivee = [n for groupe in (c.get("ordreArrivee") or []) for n in groupe]
            courses.append({
                "id": f"R{c['numReunion']}C{c['numOrdre']}",
                "reunion": c["numReunion"], "course": c["numOrdre"],
                "hippodrome": hippo.title(), "pays": pays,
                "libelle": str(c.get("libelle", "")).title(),
                "discipline": DISCIPLINES.get(c.get("discipline"), "Non précisée"),
                "distance": c.get("distance"), "heure": _heure(c.get("heureDepart")),
                "partants": c.get("nombreDeclaresPartants"),
                "statut": STATUTS.get(c.get("statut"), "à venir"),
                "arrivee": [str(n) for n in arrivee],
            })
    return courses


def programme(jour):
    return lire_programme(_get(f"{BASE}/{date_pmu(jour)}"))


def depart_passe(c, jour, maintenant=None):
    """L'heure de départ est-elle passée ? (le statut du PMU n'est pas toujours mis à jour)"""
    maintenant = maintenant or datetime.now(tz=PARIS)
    if jour < maintenant.date():
        return True
    if jour > maintenant.date() or c.get("heure", "?") == "?":
        return False
    return c["heure"] <= maintenant.strftime("%H:%M")


def libelle_course(c):
    etat = "" if c["statut"] == "à venir" else f" — {c['statut']}"
    pays = "" if c["pays"] in ("FRA", "") else f" ({c['pays']})"
    return (f"{c['id']} · {c['heure']} · {c['hippodrome']}{pays} · {c['discipline']} · "
            f"{c['libelle']} ({c['partants']} partants){etat}")


# --- Partants --------------------------------------------------------------

def _musique(texte):
    """« 2s5s1s(25)3s » -> « 2s 5s 1s (25) 3s »."""
    return " ".join(re.findall(r'\(\d{2}\)|\d{1,2}[a-zA-Z]|[A-Z][a-z]', str(texte or "")))


def lire_partants(data):
    """DataFrame au même format que turf_logic.extraire_data_pro (non-partants exclus)."""
    lignes = []
    for p in data.get("participants", []):
        if p.get("statut") != "PARTANT":
            continue
        num = str(p["numPmu"])
        nom = re.sub(r'\s+(AA|PS|AQPS)$', '', str(p.get("nom", "")).strip()).upper()
        rapport = (p.get("dernierRapportDirect") or p.get("dernierRapportReference") or {}).get("rapport")
        cote = float(rapport) if rapport else None
        musique = _musique(p.get("musique"))
        morceaux = [FERRURES.get(p.get("deferre"), "F"), musique or "N/A"]
        if p.get("sexe") and p.get("age"):
            morceaux.append(f"{SEXES.get(p['sexe'], p['sexe'][:1])}/{p['age']}")
        poids = p.get("poidsConditionMonte") or p.get("handicapPoids")  # poids réellement porté, en hg
        if poids:
            morceaux.append(f"{poids / 10:g} kg")
        humain = p.get("driver") or p.get("jockey")
        if humain or p.get("entraineur"):
            morceaux.append(f"{humain or '?'} / {p.get('entraineur') or '?'}")
        if cote is not None:
            morceaux.append(f"cote {cote:g}")
        lignes.append({"FULL_ID": f"{num} - {nom}", "NUM": num, "NOM": nom, "COTE": cote,
                       "MUSIQUE": musique, "Info": " | ".join(morceaux)})
    df = pd.DataFrame(lignes, columns=["FULL_ID", "NUM", "NOM", "COTE", "MUSIQUE", "Info"])
    return df.sort_values("NUM", key=lambda s: s.astype(int)).reset_index(drop=True) if not df.empty else df


def partants(jour, reunion, course):
    return lire_partants(_get(f"{BASE}/{date_pmu(jour)}/R{reunion}/C{course}/participants"))


# --- Cotes probables du Simple Placé -------------------------------------------
# Attention : pour une course partie, ce sont les cotes de clôture (publiées après le départ).

def lire_cotes_place(data):
    """{numéro: (cote probable minimale, maximale)} du Simple Placé."""
    return {str(r["numPmu"]): (r["minRapportProbable"], r.get("maxRapportProbable") or r["minRapportProbable"])
            for r in (data or {}).get("rapportsParticipant", []) if r.get("minRapportProbable")}


def cotes_place(jour, reunion, course):
    return lire_cotes_place(_get(f"{BASE}/{date_pmu(jour)}/R{reunion}/C{course}/rapports/SIMPLE_PLACE"))


# --- Arrivée et rapports ------------------------------------------------------

def _lire_rapports(data, type_pari):
    for pari in data or []:
        if pari.get("typePari") == type_pari:
            return {str(r["combinaison"]): r["dividendePourUnEuro"] / 100
                    for r in pari.get("rapports", []) if str(r.get("combinaison", "")).isdigit()}
    return {}


def lire_rapports_gagnant(data):
    """{numéro: euros rapportés pour 1 € en Simple Gagnant} (les dividendes sont en centimes)."""
    return _lire_rapports(data, "SIMPLE_GAGNANT")


def lire_rapports_place(data):
    """{numéro: euros rapportés pour 1 € en Simple Placé}, pour chaque cheval placé."""
    return _lire_rapports(data, "SIMPLE_PLACE")


def arrivee(date_course, reunion, course):
    """{"terminee", "annulee", "gagnant", "ordre", "rapports_gagnant", "rapports_place",
    "non_partants"} (date « 21112026 »)."""
    data = _get(f"{BASE}/{date_course}")
    infos = next((c for c in lire_programme(data) if c["reunion"] == reunion and c["course"] == course), None)
    if infos is None:
        raise PmuErreur("Course introuvable au PMU.")
    terminee = infos["statut"] == "terminée" and bool(infos["arrivee"])
    definitifs, non_partants = None, []
    if terminee:
        # sans cette liste, un non-partant serait compté perdu : en cas d'échec on ne règle rien
        participants = _get(f"{BASE}/{date_course}/R{reunion}/C{course}/participants").get("participants", [])
        non_partants = [str(p["numPmu"]) for p in participants if p.get("statut") == "NON_PARTANT"]
        try:
            definitifs = _get(f"{BASE}/{date_course}/R{reunion}/C{course}/rapports-definitifs")
        except PmuErreur:
            definitifs = None
    return {"terminee": terminee, "annulee": infos["statut"] == "annulée",
            "gagnant": infos["arrivee"][0] if terminee else None,
            "ordre": infos["arrivee"], "rapports_gagnant": lire_rapports_gagnant(definitifs),
            "rapports_place": lire_rapports_place(definitifs),
            "non_partants": non_partants}


def decouper_id(course_id):
    """« R1C3 » -> (1, 3)."""
    m = re.fullmatch(r'R(\d+)C(\d+)', str(course_id or ""))
    if not m:
        raise ValueError(course_id)
    return int(m.group(1)), int(m.group(2))
