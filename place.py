"""Conseil Simple Placé, fondé uniquement sur les données du PMU (aucune requête Gemini).

Principe : les cotes du Simple Gagnant donnent les chances de victoire de chaque cheval ;
la formule de Harville en déduit ses chances de finir placé. Quand la cote probable du
Placé est plus généreuse que ces chances ne le justifient, le pari a de la valeur.

Règle confirmée sur des courses passées (fixée avant le test de confirmation) :
  - candidats : Simple Placé dont la cote probable MINIMALE est entre 1 et 20 ;
  - gain espéré = chances de placé (Harville) × cote probable minimale − 1 ≥ +10 % ;
  - on retient le candidat au meilleur critère de Kelly.
  Résultats (1 € par conseil, rapports officiels) : 22/09-31/10/2026, 1 189 courses,
  299 conseils, +22 % (intervalle à 90 % : +6 % à +40 %) ; 01-20/11/2026, 180 conseils, +11 %.

Limites : la formule de Harville surestime les chances de placé des favoris (62 % prévus,
50 % réels dans le test) ; les cotes bougent jusqu'au départ ; résultats passés, pas une garantie.
"""
import math

import numpy as np
import pandas as pd

GAIN_ESPERE_MIN = 0.10
COTE_PLACE_MAX = 20
# Mise fixe en % du capital : les chances de placé étant surestimées, un dosage de Kelly serait trompeur
MISE_PLACE = {"Prudent": 0.005, "Équilibré": 0.01, "Offensif": 0.015}


def nombre_places(nb_partants):
    """Règle du PMU : 3 places payées à partir de 8 partants, 2 de 4 à 7."""
    return 3 if nb_partants >= 8 else 2


def harville_place(p, k):
    """Chances de finir dans les k premiers (k = 2 ou 3), à partir des chances de victoire p."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    top = np.zeros(n)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            pij = p[i] * p[j] / (1 - p[i])
            if k == 2:
                top[i] += pij
                top[j] += pij
                continue
            for m in range(n):
                if m in (i, j):
                    continue
                pijm = pij * p[m] / (1 - p[i] - p[j])
                top[i] += pijm
                top[j] += pijm
                top[m] += pijm
    return top


def _croissance(prob, cote, fraction=0.25):
    f = fraction * (prob * cote - 1) / (cote - 1)
    return prob * math.log(1 + f * (cote - 1)) + (1 - prob) * math.log(1 - f)


def conseil_place(df, cotes_place, profil, capital, budget_restant=None):
    """Meilleur Simple Placé de la course, ou None.

    df : partants (NUM, NOM, COTE = cote du Simple Gagnant) ; cotes_place : {num: (min, max)}.
    Retourne {"num", "nom", "proba", "cote_min", "cote_max", "gain_espere", "cote_mini_a_jouer", "mise"}.
    """
    if df.empty or df["COTE"].isna().any() or len(df) < 4:
        return None
    inv = 1 / df["COTE"].astype(float).to_numpy()
    q = inv / inv.sum()
    probas = harville_place(q, nombre_places(len(df)))
    candidats = []
    for i, (_, row) in enumerate(df.iterrows()):
        cotes = cotes_place.get(str(row["NUM"]))
        if not cotes:
            continue
        cote_min, cote_max = cotes
        if not (1 < cote_min <= COTE_PLACE_MAX):
            continue
        gain = probas[i] * cote_min - 1
        if gain >= GAIN_ESPERE_MIN:
            candidats.append((_croissance(probas[i], cote_min), i, row, cote_min, cote_max, gain))
    if not candidats:
        return None
    _, i, row, cote_min, cote_max, gain = max(candidats, key=lambda c: c[0])
    mise = round(max(float(capital), 0) * MISE_PLACE[profil], 2)
    if budget_restant is not None:
        mise = round(max(min(mise, budget_restant), 0), 2)
    return {"num": str(row["NUM"]), "nom": row["NOM"], "proba": float(probas[i]),
            "cote_min": cote_min, "cote_max": cote_max, "gain_espere": float(gain),
            # en dessous de cette cote minimale, le gain espéré passe sous le seuil de la règle
            "cote_mini_a_jouer": round(float((1 + GAIN_ESPERE_MIN) / probas[i]), 2), "mise": mise}


# --- Suivi à blanc ---------------------------------------------------------------

COLONNES_SUIVI = ["id", "date", "date_course", "course", "hippodrome", "num", "nom", "proba",
                  "cote_min", "mise", "resultat", "rapport", "gain"]


def ligne_suivi(identifiant, date, date_course, course, hippo, conseil):
    return {"id": identifiant, "date": date, "date_course": date_course, "course": course,
            "hippodrome": hippo, "num": conseil["num"], "nom": conseil["nom"],
            "proba": round(conseil["proba"], 3), "cote_min": conseil["cote_min"], "mise": conseil["mise"],
            "resultat": "En attente", "rapport": 0.0, "gain": 0.0}


def ajouter_suivi(df, ligne):
    """Un seul conseil par course : le plus récent (le plus proche du départ) remplace l'ancien."""
    df = df.copy() if df is not None else pd.DataFrame(columns=COLONNES_SUIVI)
    meme = (df["course"].astype(str) == ligne["course"]) & (df["date_course"].astype(str) == ligne["date_course"])
    return pd.concat([df[~meme], pd.DataFrame([ligne])], ignore_index=True)[COLONNES_SUIVI]


def regler(df, i, arrivee):
    """Règle le conseil i avec l'arrivée PMU (pmu.arrivee). Retourne True si réglé."""
    if arrivee["annulee"]:
        df.at[i, "resultat"], df.at[i, "rapport"], df.at[i, "gain"] = "Annulée", 1.0, 0.0
        return True
    if not arrivee["terminee"]:
        return False
    num = str(df.at[i, "num"])
    rapport = float(arrivee["rapports_place"].get(num, 0.0))
    if not rapport and num in arrivee["ordre"][:3] and not arrivee["rapports_place"]:
        return False  # rapports officiels pas encore publiés
    mise = float(df.at[i, "mise"] or 0)
    df.at[i, "resultat"] = "Placé" if rapport else "Non placé"
    df.at[i, "rapport"] = rapport
    df.at[i, "gain"] = round(mise * rapport - mise, 2)
    return True


def stats_suivi(df):
    """Bilan des conseils réglés : rendement pour 1 € par conseil et gain avec les mises conseillées."""
    if df is None or df.empty:
        return {"n": 0, "en_attente": 0}
    regles = df[df["resultat"].isin(["Placé", "Non placé"])]
    attente = int((df["resultat"] == "En attente").sum())
    n = len(regles)
    if not n:
        return {"n": 0, "en_attente": attente}
    rapports = pd.to_numeric(regles["rapport"], errors="coerce").fillna(0)
    return {"n": n, "en_attente": attente,
            "places": float((regles["resultat"] == "Placé").mean()),
            "rendement": float(rapports.mean() - 1),
            "gain": float(pd.to_numeric(regles["gain"], errors="coerce").fillna(0).sum()),
            "mise": float(pd.to_numeric(regles["mise"], errors="coerce").fillna(0).sum())}
