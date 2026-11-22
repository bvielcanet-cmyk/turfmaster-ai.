"""Mesure de la précision : l'IA prévoit-elle mieux que les cotes ?

Chaque analyse est enregistrée avec, pour chaque partant, la probabilité de victoire
selon l'IA et selon les cotes. Quand le gagnant est connu, on compare les deux avec
deux scores classiques (plus bas = meilleur) :

- score de Brier : somme des (probabilité − résultat)² sur les partants (résultat = 1
  pour le gagnant, 0 sinon) ;
- perte logarithmique : −ln(probabilité donnée au gagnant).

Cette mesure est informative : elle ne sert à choisir aucun pari. Pour une course analysée après coup,
les cotes sont celles de la clôture, publiées après le départ.
"""
import json
import math

import pandas as pd

COLONNES_ANALYSES = ["id", "date", "date_course", "course", "hippodrome", "discipline", "profil",
                     "partants", "decision", "pari_num", "mise", "gagnant", "source_resultat"]
MINIMUM_COURSES = 100
COLONNES_NUMERIQUES = {"mise", "gain_reel", "cote", "proba_ia", "gain_espere", "proba", "cote_min",
                       "rapport", "gain", "cote_gagnant"}


def texte_cellule(valeur):
    """Valeur d'une cellule relue (Google Sheets ou CSV) -> texte propre.

    Google Sheets ne garde pas les types : à la relecture, une cellule vide devient NaN
    et « 5 » peut revenir en 5.0. On ramène tout à « » ou « 5 »."""
    if valeur is None:
        return ""
    try:
        if pd.isna(valeur):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(valeur, float) and valeur.is_integer():
        return str(int(valeur))
    texte = str(valeur).strip()
    return "" if texte.lower() == "nan" else texte


def normaliser(df):
    """Colonnes de texte en texte propre, montants en nombres (0 si vide)."""
    df = df.copy()
    for col in df.columns:
        if col in COLONNES_NUMERIQUES:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)
        else:
            df[col] = df[col].map(texte_cellule).astype(object)
    return df


def ligne_analyse(identifiant, date, date_course, course, hippo, discipline, chances):
    """Ligne à enregistrer pour une analyse (chances = sortie de turf_logic.comparer_chances)."""
    partants = {}
    for _, l in chances.iterrows():
        partants[str(l["num"])] = {
            "nom": l["nom"],
            "ia": None if pd.isna(l["proba_ia"]) else round(float(l["proba_ia"]), 4),
            "cotes": None if pd.isna(l["proba_marche"]) else round(float(l["proba_marche"]), 4),
            "cote": None if pd.isna(l["cote"]) else float(l["cote"]),
        }
    return {"id": identifiant, "date": date, "date_course": date_course or "", "course": course or "",
            "hippodrome": hippo, "discipline": discipline, "profil": "",
            "partants": json.dumps(partants, ensure_ascii=False),
            "decision": "Information", "pari_num": "", "mise": 0.0,
            "gagnant": "", "source_resultat": ""}


def ajouter_analyse(df, ligne):
    """Ajoute l'analyse. Une course PMU déjà analysée (même jour) est remplacée :
    seule la dernière analyse compte, pour ne pas compter deux fois la même course."""
    df = df.copy() if df is not None else pd.DataFrame(columns=COLONNES_ANALYSES)
    if ligne["course"]:
        meme = ((df["course"].map(texte_cellule) == ligne["course"])
                & (df["date_course"].map(texte_cellule).str.zfill(8) == ligne["date_course"]))
        df = df[~meme]
    return pd.concat([df, pd.DataFrame([ligne])], ignore_index=True)[COLONNES_ANALYSES]


def _courses_mesurables(df):
    """[(probas IA, probas cotes, gagnant)] pour les analyses dont le gagnant est connu."""
    courses = []
    if df is None or df.empty:
        return courses
    for _, row in df.iterrows():
        gagnant = texte_cellule(row.get("gagnant"))
        if not gagnant:
            continue
        try:
            partants = json.loads(row["partants"])
        except (TypeError, ValueError):
            continue
        ia = {n: v["ia"] for n, v in partants.items() if v.get("ia") is not None and v.get("cotes") is not None}
        cotes = {n: v["cotes"] for n, v in partants.items() if n in ia}
        if gagnant not in ia or not ia:
            continue
        total = sum(ia.values()) or 1
        courses.append(({n: p / total for n, p in ia.items()}, cotes, gagnant))
    return courses


def _brier(probas, gagnant):
    return sum((p - (1 if n == gagnant else 0)) ** 2 for n, p in probas.items())


def _perte_log(p_gagnant):
    return -math.log(max(p_gagnant, 0.01))


def scores(df):
    """Compare l'IA et les cotes sur les courses dont le gagnant est connu."""
    courses = _courses_mesurables(df)
    n = len(courses)
    if not n:
        return {"n": 0}
    resultat = {
        "n": n,
        "brier_ia": sum(_brier(ia, g) for ia, _, g in courses) / n,
        "brier_cotes": sum(_brier(c, g) for _, c, g in courses) / n,
        "log_ia": sum(_perte_log(ia[g]) for ia, _, g in courses) / n,
        "log_cotes": sum(_perte_log(c[g]) for _, c, g in courses) / n,
        "favori_ia": sum(max(ia, key=ia.get) == g for ia, _, g in courses) / n,
        "favori_cotes": sum(max(c, key=c.get) == g for _, c, g in courses) / n,
    }
    return resultat


# --- Résultats -----------------------------------------------------------------

def en_attente(df):
    """Analyses dont le gagnant n'est pas encore connu."""
    if df is None or df.empty:
        return df
    return df[df["gagnant"].map(texte_cellule) == ""]
