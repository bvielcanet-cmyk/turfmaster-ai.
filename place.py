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
# Harville corrigé (Lo & Bacon-Shone) : coefficients appris sur 1 195 courses PMU (22/09-31/10/2026),
# mieux calibré en novembre (score de Brier 0,1514 contre 0,1523). Études publiées : 0,76 et 0,62.
LAMBDA_2E, LAMBDA_3E = 0.81, 0.65
REGLES = {"confirmée": (1.0, 1.0), "corrigée": (LAMBDA_2E, LAMBDA_3E)}
COTE_PLACE_MAX = 20
# Mise fixe en % du capital : les chances de placé étant surestimées, un dosage de Kelly serait trompeur
MISE_PLACE = {"Prudent": 0.005, "Équilibré": 0.01, "Offensif": 0.015}


def nombre_places(nb_partants):
    """Règle du PMU : 3 places payées à partir de 8 partants, 2 de 4 à 7."""
    return 3 if nb_partants >= 8 else 2


def harville_place(p, k, l2=1.0, l3=1.0):
    """Chances de finir dans les k premiers (k = 2 ou 3), à partir des chances de victoire p.

    l2, l3 = 1 : formule de Harville classique ; < 1 : version corrigée, qui réduit l'avantage
    des favoris pour les 2e et 3e places (ils y sont moins souvent que Harville ne le prévoit)."""
    p = np.asarray(p, dtype=float)
    p2, p3 = p ** l2, p ** l3
    n = len(p)
    top = np.zeros(n)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            pij = p[i] * p2[j] / (p2.sum() - p2[i])
            if k == 2:
                top[i] += pij
                top[j] += pij
                continue
            for m in range(n):
                if m in (i, j):
                    continue
                pijm = pij * p3[m] / (p3.sum() - p3[i] - p3[j])
                top[i] += pijm
                top[j] += pijm
                top[m] += pijm
    return top


def _croissance(prob, cote, fraction=0.25):
    f = fraction * (prob * cote - 1) / (cote - 1)
    return prob * math.log(1 + f * (cote - 1)) + (1 - prob) * math.log(1 - f)


def conseil_place(df, cotes_place, profil, capital, budget_restant=None, regle="confirmée"):
    """Meilleur Simple Placé de la course, ou None.

    df : partants (NUM, NOM, COTE = cote du Simple Gagnant) ; cotes_place : {num: (min, max)}.
    regle : « confirmée » (Harville classique, validée sur des courses passées) ou « corrigée »
    (Harville corrigé, en essai). Retourne {"num", "nom", "proba", "proba_corrigee", "cote_min",
    "cote_max", "gain_espere", "cote_mini_a_jouer", "mise", "regle"}.
    """
    if df.empty or df["COTE"].isna().any() or len(df) < 4:
        return None
    inv = 1 / df["COTE"].astype(float).to_numpy()
    q = inv / inv.sum()
    k = nombre_places(len(df))
    probas = harville_place(q, k, *REGLES[regle])
    corrigees = harville_place(q, k, LAMBDA_2E, LAMBDA_3E)
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
            "proba_corrigee": float(corrigees[i]), "regle": regle, "cote_gagnant": float(row["COTE"]),
            "cote_min": cote_min, "cote_max": cote_max, "gain_espere": float(gain),
            # en dessous de cette cote minimale, le gain espéré passe sous le seuil de la règle
            "cote_mini_a_jouer": round(float((1 + GAIN_ESPERE_MIN) / probas[i]), 2), "mise": mise}


# --- Suivi à blanc ---------------------------------------------------------------

COLONNES_SUIVI = ["id", "date", "date_course", "course", "hippodrome", "num", "nom", "proba",
                  "cote_min", "mise", "resultat", "rapport", "gain", "regle", "source", "cote_gagnant"]


def ligne_suivi(identifiant, date, date_course, course, hippo, conseil, source="application"):
    return {"regle": conseil.get("regle", "confirmée"), "source": source,
            "cote_gagnant": conseil.get("cote_gagnant", 0.0),
            "id": identifiant, "date": date, "date_course": date_course, "course": course,
            "hippodrome": hippo, "num": conseil["num"], "nom": conseil["nom"],
            "proba": round(conseil["proba"], 3), "cote_min": conseil["cote_min"], "mise": conseil["mise"],
            "resultat": "En attente", "rapport": 0.0, "gain": 0.0}


def ajouter_suivi(df, ligne):
    """Un seul conseil par course et par règle : le plus récent (le plus proche du départ) remplace l'ancien."""
    df = df.copy() if df is not None else pd.DataFrame(columns=COLONNES_SUIVI)
    regle_df = df["regle"].astype(str).replace("", "confirmée")
    meme = ((df["course"].astype(str) == ligne["course"]) & (df["date_course"].astype(str) == ligne["date_course"])
            & (regle_df == ligne["regle"]))
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


def stats_suivi(df, regle=None, outsiders=False):
    """Bilan des conseils réglés : rendement pour 1 € par conseil et gain avec les mises conseillées.
    regle : ne compter que cette règle (les anciennes lignes sans règle comptent comme « confirmée »)."""
    if df is None or df.empty:
        return {"n": 0, "en_attente": 0}
    if regle:
        df = df[df["regle"].astype(str).replace("", "confirmée") == regle]
    if outsiders:  # conseils sur des chevaux de cote Gagnant >= 8 (le « joker outsider »)
        df = df[pd.to_numeric(df["cote_gagnant"], errors="coerce").fillna(0) >= 8]
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
