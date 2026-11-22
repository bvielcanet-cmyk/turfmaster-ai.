"""Aide à la décision : lisibilité d'une course, podium estimé et risque d'un pari choisi par l'utilisateur.

Ce module ne choisit aucun pari et ne conseille aucune mise. Les cotes résument l'avis de tous les
parieurs : elles disent qui a des chances, pas quel pari est rentable.

Règle pour toute étude future : une cote utilisée pour CHOISIR un pari doit être horodatée avant le
départ. Les cotes que le PMU renvoie pour une course terminée (dernierRapportDirect, cotes probables)
sont celles de la clôture, publiées après le départ.
"""
import itertools

import numpy as np
import pandas as pd

import pmu

# Harville corrigé (Lo & Bacon-Shone) : réduit l'avantage des favoris pour les 2e et 3e places
LAMBDA_2E, LAMBDA_3E = 0.81, 0.65

# Le feu dit si la course est LISIBLE, jamais si elle est rentable. Seuils fixés avant de les mesurer.
SEUIL_VERT, SEUIL_ORANGE = 0.35, 0.22
FEUX = {
    "vert": {"emoji": "🟢", "titre": "COURSE CLAIRE", "phrase": "Un favori se détache nettement."},
    "orange": {"emoji": "🟠", "titre": "COURSE DISPUTÉE", "phrase": "Un favori, mais de vrais rivaux."},
    "rouge": {"emoji": "🔴", "titre": "COURSE TRÈS OUVERTE", "phrase": "Aucun cheval ne se détache : surprise possible."},
}

# Mesuré du 22/09 au 20/11/2026 sur 1 774 courses PMU, avec des cotes horodatées au moins 10 min avant le
# départ (30 min en médiane). Ces repères décrivent le passé : aucun réglage n'en a été tiré.
REPERES = {
    "vert": {"courses": 481, "gagne": .414, "place": .703, "trio": .125},
    "orange": {"courses": 709, "gagne": .269, "place": .583, "trio": .067},
    "rouge": {"courses": 584, "gagne": .199, "place": .409, "trio": .045},
}

AUTRES_PARIS = """**Aucun pari testé n'est rentable.** Test : à chaque course, jouer les chevaux préférés des parieurs
environ 30 minutes avant le départ, payé aux rapports officiels du PMU (22/09 au 20/11/2026).

| Pari | Passe | Perte moyenne pour 10 € | Courses |
|---|--:|--:|--:|
| 🏅 Simple Placé | 56 % | 1,13 € | 1 774 |
| 🏆 Simple Gagnant | 29 % | 1,51 € | 1 774 |
| 👯 Couplé Placé | 25 % | 1,56 € | 1 598 |
| 👯 Couplé Gagnant | 13 % | 1,67 € | 1 598 |
| 🎯 2 sur 4 | 31 % | 2,24 € | 1 311 |
| 🥉 Trio | 7 % | 2,78 € | 1 530 |
| 👯 Couplé Ordre | 11 % | 4,68 € | 176 |
| 🎰 Super 4 | 2 % | 5,56 € | 423 |
| 🎰 Trio Ordre | 5 % | 6,14 € | 175 |

Multi, Tiercé, Quarté+, Quinté+ et Pick 5 n'ont pas été testés. Un feu vert ne rend aucun pari rentable."""

GAGNANT, PLACE = "Simple Gagnant", "Simple Placé"
COLONNES_ORDRE = ["rang", "num", "nom", "cote", "victoire", "place"]


def nombre_places(nb_partants):
    """Règle du PMU : 3 places payées à partir de 8 partants, 2 de 4 à 7."""
    return 3 if nb_partants >= 8 else 2


def podiums(p, k):
    """{(1er, 2e[, 3e]): probabilité}, à partir des chances de victoire p."""
    p = np.asarray(p, dtype=float)
    puissances = [p, p ** LAMBDA_2E, p ** LAMBDA_3E]
    totaux = [x.sum() for x in puissances]
    resultat = {}
    for issue in itertools.permutations(range(len(p)), k):
        proba = 1.0
        for rang, i in enumerate(issue):
            exclus = sum(puissances[rang][j] for j in issue[:rang])
            proba *= puissances[rang][i] / (totaux[rang] - exclus)
        resultat[issue] = proba
    return resultat


def ordre_estime(df):
    """Partants du plus au moins probable. Vide si une cote manque ou s'il y a moins de 4 partants."""
    if len(df) < 4 or df["COTE"].isna().any() or (df["COTE"].astype(float) <= 0).any():
        return pd.DataFrame(columns=COLONNES_ORDRE)
    inverses = 1 / df["COTE"].astype(float).to_numpy()
    q = inverses / inverses.sum()
    places = np.zeros(len(q))
    for issue, proba in podiums(q, nombre_places(len(q))).items():
        places[list(issue)] += proba
    ordre = pd.DataFrame({"num": df["NUM"].astype(str).to_numpy(), "nom": df["NOM"].to_numpy(),
                          "cote": df["COTE"].astype(float).to_numpy(), "victoire": q, "place": places})
    ordre = ordre.sort_values("victoire", ascending=False, kind="stable").reset_index(drop=True)
    return ordre.assign(rang=range(1, len(ordre) + 1))[COLONNES_ORDRE]


def feu(ordre):
    """« vert », « orange », « rouge », ou None si les cotes ne permettent pas de juger."""
    if ordre.empty:
        return None
    favori = float(ordre.iloc[0]["victoire"])
    return "vert" if favori >= SEUIL_VERT else "orange" if favori >= SEUIL_ORANGE else "rouge"


def chances_trio(ordre):
    """(dans le désordre, dans l'ordre exact) pour les 3 premiers estimés ; None sous 8 partants."""
    if len(ordre) < 8:
        return None
    issues = podiums(ordre["victoire"], 3)
    return sum(issues[i] for i in itertools.permutations(range(3))), issues[(0, 1, 2)]


def risque_pari(chance, cote, mise):
    """Ce que risque un pari choisi par l'utilisateur.

    « cout_moyen » vaut None quand le calcul annonce un gain moyen : ce calcul s'est révélé trompeur
    (voir README), on ne l'affiche donc jamais comme un avantage."""
    moyen = mise * (chance * cote - 1)
    return {"perte": float(mise), "risque": 1 - chance, "gain": float(mise * (cote - 1)),
            "cout_moyen": float(-moyen) if moyen < 0 else None}


def cribler(jour, maintenant, programme, lire_partants):
    """Courses françaises qui ne sont pas encore parties, de la plus claire à la plus ouverte."""
    lignes = []
    for c in programme:
        if c["pays"] != "FRA" or c["statut"] != "à venir" or pmu.depart_passe(c, jour, maintenant):
            continue
        try:
            ordre = ordre_estime(lire_partants(jour, c["reunion"], c["course"]))
        except pmu.PmuErreur:
            continue
        couleur = feu(ordre)
        if couleur:
            f = ordre.iloc[0]
            lignes.append({"course": c["id"], "heure": c["heure"], "hippodrome": c["hippodrome"], "feu": couleur,
                           "favori": f"n° {f['num']} {f['nom']}", "victoire": float(f["victoire"]),
                           "place": float(f["place"]), "partants": len(ordre)})
    return sorted(lignes, key=lambda x: x["victoire"], reverse=True)
