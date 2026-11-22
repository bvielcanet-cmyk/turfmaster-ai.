"""Aide à la décision : lisibilité d'une course, pronostics chiffrés, conseil et risque d'un pari.

Le conseil désigne le pari le PLUS PROBABLE, jamais un pari rentable : aucun ne l'est de façon fiable.
La mise conseillée est un plafond tiré du budget. Les cotes résument l'avis de tous les parieurs.

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

Quarté+, Quinté+ et Pick 5 n'ont pas été testés. Multi et Tiercé : seules leurs chances ont été mesurées ici. Un feu vert ne rend aucun pari rentable."""

GAGNANT, PLACE = "Simple Gagnant", "Simple Placé"
SEUIL_PRONOSTIC = 0.30
MISE_MINI, MISE_MAXI, PARIS_PAR_JOUR = 2.0, 10.0, 3  # 2 € = mise de base du Simple en point de vente
PART_BUDGET = {"vert": 0.10, "orange": 0.05, "rouge": 0.0}  # par pari, du budget de 7 jours
PERTE_PLACE = {"vert": 0.061, "orange": 0.062, "rouge": 0.216}  # favori placé, perte moyenne mesurée

# Pronostic par type de pari, toujours sur les chevaux les moins cotés.
# k chevaux choisis, rangs visés (None : places payées). « correction » : (a, b) de a + b·logit(p), apprise
# sur sept.-oct. 2026 et gardée seulement si elle prévoyait mieux novembre. « bilan » : courses passées où
# la chance annoncée dépassait 30 %. Aucun pari n'y est rentable de façon fiable.
PRONOSTICS = {
    "SIMPLE_PLACE": [("🏅 Simple Placé", 1, None, (-0.1017, 0.8902), "perd 11 % en moyenne")],
    "SIMPLE_GAGNANT": [("🏆 Simple Gagnant", 1, 1, (-0.2409, 0.7567), "perd 13 % en moyenne")],
    "COUPLE_PLACE": [("👯 Couplé Placé", 2, 3, (0.1141, 1.0204),
                      "perd 2 % en moyenne, très incertain (de −12 à +9 %)")],
    "COUPLE_GAGNANT": [("👯 Couplé Gagnant", 2, 2, (0.3134, 1.0918), "46 cas seulement, peu fiable")],
    "DEUX_SUR_QUATRE": [("🎯 2 sur 4", 2, 4, None, "perd 20 % en moyenne, chances un peu surestimées")],
    "TRIO": [("🥉 Trio", 3, 3, (0.5221, 1.0771), "10 cas seulement, peu fiable")],
    "MINI_MULTI": [("🎰 Mini Multi en 6", 6, 4, (0.0810, 1.0471), "perd 20 % en moyenne"),
                   ("🎰 Mini Multi en 5", 5, 4, (0.3474, 1.2145), "9 cas seulement, peu fiable")],
    "MULTI": [("🎰 Multi en 7", 7, 4, None, "33 cas seulement, peu fiable"),
              ("🎰 Multi en 6", 6, 4, None, "2 cas seulement, peu fiable")],
}

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


def corriger(p, coefficients):
    if not coefficients or not 0 < p < 1:
        return float(p)
    a, b = coefficients
    return float(1 / (1 + np.exp(-(a + b * np.log(p / (1 - p))))))


def chances_favori(ordre):
    """(gagner, être placé) du favori, corrigées : le calcul brut surestimait les grands favoris."""
    f = ordre.iloc[0]
    return (corriger(f["victoire"], PRONOSTICS["SIMPLE_GAGNANT"][0][3]),
            corriger(f["place"], PRONOSTICS["SIMPLE_PLACE"][0][3]))


def chance_selection(p, k, rangs):
    """Chance que les k premiers chevaux estimés soient dans les « rangs » premiers (k <= rangs),
    ou qu'ils contiennent ces premiers (k > rangs)."""
    p, choisis = np.asarray(p, dtype=float), set(range(k))
    if max(k, rangs) > len(p):
        return 0.0
    if k >= rangs:
        issues = list(itertools.permutations(range(k), rangs))
    else:
        issues = [i for i in itertools.permutations(range(len(p)), rangs) if choisis <= set(i)]
    indices, total = np.array(issues), np.ones(len(issues))
    for rang, exposant in enumerate((1.0, LAMBDA_2E, LAMBDA_3E, LAMBDA_3E)[:rangs]):
        poids = p ** exposant
        total *= poids[indices[:, rang]] / (poids.sum() - poids[indices[:, :rang]].sum(axis=1))
    return float(total.sum())


def pronostics(ordre, offerts=None):
    """Paris proposés sur la course dont la chance dépasse 30 %, du plus au moins probable.
    offerts=None (course collée) : seuls les paris Simples sont sûrs d'exister."""
    if ordre.empty:
        return []
    offerts = {"SIMPLE_PLACE", "SIMPLE_GAGNANT"} if not offerts else set(offerts)
    resultat = []
    for code, variantes in PRONOSTICS.items():
        if code not in offerts:
            continue
        for nom, k, rangs, coefficients, bilan in variantes:
            rangs = rangs or nombre_places(len(ordre))
            if code == "SIMPLE_PLACE":
                p = ordre.iloc[0]["place"]
            else:
                p = chance_selection(ordre["victoire"], k, rangs)
            p = corriger(p, coefficients)
            if p > SEUIL_PRONOSTIC:
                resultat.append({"code": code, "pari": nom, "chevaux": " - ".join(ordre["num"].head(k)),
                                 "chance": p, "bilan": bilan})
    return sorted(resultat, key=lambda x: x["chance"], reverse=True)


def mise_conseillee(couleur, budget, deja_mise, paris_du_jour=0):
    """Plafond conseillé pour un pari. 0 : passer (course rouge, budget épuisé, 3 paris déjà faits)."""
    part, reste = PART_BUDGET.get(couleur, 0.0), budget - deja_mise
    if not part or reste < MISE_MINI or paris_du_jour >= PARIS_PAR_JOUR:
        return 0.0
    return float(np.floor(min(max(budget * part, MISE_MINI), MISE_MAXI, reste) * 2) / 2)


def conseiller(ordre, budget, deja_mise, paris_du_jour=0, offerts=None):
    """Le conseil d'une course : le favori en Simple Placé, ou passer."""
    couleur = feu(ordre)
    if couleur is None:
        return None
    mise, raison = 0.0, ""
    if offerts and "SIMPLE_PLACE" not in offerts:
        raison = "Le Simple Placé n'est pas proposé sur cette course."
    elif couleur == "rouge":
        raison = "Course trop ouverte : le favori placé y perd 22 % de la mise en moyenne."
    elif paris_du_jour >= PARIS_PAR_JOUR:
        raison = f"Déjà {PARIS_PAR_JOUR} paris notés aujourd'hui : c'est le maximum conseillé."
    else:
        mise = mise_conseillee(couleur, budget, deja_mise)
        if not mise:
            raison = "Votre budget des 7 jours ne permet plus de pari."
    return {"num": ordre.iloc[0]["num"], "nom": ordre.iloc[0]["nom"], "chance": chances_favori(ordre)[1],
            "mise": mise, "cout": mise * PERTE_PLACE[couleur], "raison": raison}


def repartir(lignes, budget, deja_mise, paris_du_jour=0):
    """Ajoute une mise conseillée aux courses les mieux classées, dans le budget et 3 paris par jour."""
    resultat, total, nombre = [], deja_mise, paris_du_jour
    for x in lignes:
        permis = not x["offerts"] or "SIMPLE_PLACE" in x["offerts"]
        mise = mise_conseillee(x["feu"], budget, total, nombre) if permis else 0.0
        if mise:
            total, nombre = total + mise, nombre + 1
        resultat.append({**x, "mise": mise, "cout": mise * PERTE_PLACE[x["feu"]]})
    return resultat


def chances_trio(ordre):
    """(dans le désordre, dans l'ordre exact) pour les 3 premiers estimés ; None sous 8 partants."""
    if len(ordre) < 8:
        return None
    issues = podiums(ordre["victoire"], 3)
    desordre = sum(issues[i] for i in itertools.permutations(range(3)))
    return corriger(desordre, PRONOSTICS["TRIO"][0][3]), issues[(0, 1, 2)]


def risque_pari(chance, cote, mise):
    """Ce que risque un pari choisi par l'utilisateur.

    « cout_moyen » vaut None quand le calcul annonce un gain moyen : ce calcul s'est révélé trompeur
    (voir README), on ne l'affiche donc jamais comme un avantage."""
    moyen = mise * (chance * cote - 1)
    return {"perte": float(mise), "risque": 1 - chance, "gain": float(mise * (cote - 1)),
            "cout_moyen": float(-moyen) if moyen < 0 else None}


def cribler(jour, maintenant, programme, lire_partants):
    """Courses françaises qui ne sont pas encore parties, classées par prédiction (favori placé)."""
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
            f, (gagne, place) = ordre.iloc[0], chances_favori(ordre)
            lignes.append({"course": c["id"], "heure": c["heure"], "hippodrome": c["hippodrome"], "feu": couleur,
                           "favori": f"n° {f['num']} {f['nom']}", "victoire": gagne, "place": place,
                           "partants": len(ordre), "offerts": c.get("paris") or [],
                           "pronostics": pronostics(ordre, c.get("paris"))})
    return sorted(lignes, key=lambda x: x["place"], reverse=True)
