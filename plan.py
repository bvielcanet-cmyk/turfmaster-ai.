"""Plan du jour : crible gratuit de toutes les courses (aucune requête Gemini), sélection des plus
prometteuses et répartition d'un budget selon le profil.

Le crible applique la règle Placé (voir place.py) à chaque course française à venir. Le score de
classement est le gain espéré calculé avec les chances de placé CORRIGÉES (plus réalistes que la
formule classique, qui surestime les favoris).

Important : les cotes du Placé bougent beaucoup jusqu'au départ, et la règle n'a été validée qu'avec
les dernières cotes. Un plan établi tôt dans la journée est provisoire : chaque pari doit être
reconfirmé quelques minutes avant le départ.
"""
import math
import time

import numpy as np
import pandas as pd

import place
import pmu

MARGE_MINUTES = 5
COTE_OUTSIDER = 8      # cote Gagnant à partir de laquelle un cheval est considéré comme outsider
PART_JOKER = 0.10      # part du budget pour le joker outsider (option)  # une course qui part dans moins de 5 minutes n'est plus jouable sereinement
# Mise minimale : les rapports officiels du PMU indiquent une mise de base de 2 € pour les paris simples
MISE_MIN = 2.0
PROFILS_PLAN = {
    # règles de conseil admises, chances de placé corrigées minimales, part maximale du budget par pari
    "Prudent":   {"regles": ("confirmée",), "proba_min": 0.45, "part_max": 0.40},
    "Équilibré": {"regles": ("confirmée",), "proba_min": 0.0, "part_max": 0.50},
    "Offensif":  {"regles": ("confirmée", "corrigée"), "proba_min": 0.0, "part_max": 0.60},
}


def minutes_avant(course, maintenant):
    if course.get("heure", "?") == "?":
        return None
    h, m = map(int, course["heure"].split(":"))
    return (maintenant.replace(hour=h, minute=m, second=0, microsecond=0) - maintenant).total_seconds() / 60


def evaluer_course(course, df, cotes):
    """Conseils (règle confirmée et corrigée) d'une course, avec score de valeur réaliste."""
    lignes = []
    cotes_gagnant = dict(zip(df["NUM"].astype(str), df["COTE"]))
    for regle in place.REGLES:
        c = place.conseil_place(df, cotes, "Équilibré", 0, regle=regle)
        if c is None:
            continue
        valeur = c["proba_corrigee"] * c["cote_min"] - 1  # gain espéré avec les chances corrigées
        lignes.append({"course": course["id"], "heure": course["heure"], "hippodrome": course["hippodrome"],
                       "discipline": course["discipline"], "libelle": course["libelle"], "regle": regle,
                       "num": c["num"], "nom": c["nom"], "cote_min": c["cote_min"], "cote_max": c["cote_max"],
                       "cote_mini_a_jouer": c["cote_mini_a_jouer"], "proba_corrigee": c["proba_corrigee"],
                       "gain_regle": c["gain_espere"], "valeur": valeur,
                       "cote_gagnant": float(cotes_gagnant.get(c["num"], 0) or 0),
                       "reunion": course["reunion"], "numero": course["course"]})
    return lignes


def cribler(jour, maintenant, lire_partants=pmu.partants, lire_cotes=pmu.cotes_place, programme=None,
            pause=0.3, progression=None):
    """Évalue toutes les courses françaises à venir du jour. Retourne (DataFrame des conseils, nb courses vues)."""
    programme = programme if programme is not None else pmu.programme(jour)
    a_voir = [c for c in programme if c["pays"] == "FRA" and c["statut"] == "à venir"
              and (minutes_avant(c, maintenant) or 0) >= MARGE_MINUTES]
    lignes = []
    for k, course in enumerate(a_voir):
        if progression:
            progression(k, len(a_voir), course)
        try:
            df = lire_partants(jour, course["reunion"], course["course"])
            cotes = lire_cotes(jour, course["reunion"], course["course"])
        except pmu.PmuErreur:
            continue
        lignes += evaluer_course(course, df, cotes)
        if pause:
            time.sleep(pause)
    colonnes = ["course", "heure", "hippodrome", "discipline", "libelle", "regle", "num", "nom", "cote_min",
                "cote_max", "cote_mini_a_jouer", "proba_corrigee", "gain_regle", "valeur", "cote_gagnant",
                "reunion", "numero"]
    return pd.DataFrame(lignes, columns=colonnes), len(a_voir)


def croissance(proba, cote, fraction=0.25):
    """Critère de Kelly (croissance espérée du capital) : équilibre chances et rapport ; négatif si pas de valeur."""
    if cote <= 1 or proba * cote <= 1:
        return proba * cote - 1 - 1  # sans valeur : classé après tous les paris de valeur
    f = fraction * (proba * cote - 1) / (cote - 1)
    return proba * math.log(1 + f * (cote - 1)) + (1 - proba) * math.log(1 - f)


def selectionner(conseils, profil, nombre=3):
    """Les `nombre` meilleurs paris admis par le profil, une course au plus une fois.

    Seuls les chevaux de cote Gagnant < COTE_OUTSIDER entrent dans le plan principal : c'est là que la
    règle Placé a fait ses preuves sur les courses passées (cote 1-4 : +14 %, IC 90 % +4 à +23 % ;
    4-8 : +20 %). Les outsiders relèvent du joker. Classement par critère de Kelly, avec les chances
    de placé corrigées (plus réalistes)."""
    if conseils.empty:
        return conseils
    p = PROFILS_PLAN[profil]
    admis = conseils[conseils["regle"].isin(p["regles"]) & (conseils["proba_corrigee"] >= p["proba_min"])
                     & (conseils["cote_gagnant"] < COTE_OUTSIDER)].copy()
    admis["kelly"] = [croissance(pr, c) for pr, c in zip(admis["proba_corrigee"], admis["cote_min"])]
    admis = admis.sort_values(["kelly", "valeur"], ascending=False)
    return admis.drop_duplicates("course").head(nombre).reset_index(drop=True)


def repartir(selection, budget, profil, budget_pertes=None):
    """Mises (arrondies à 0,50 € inférieur) au prorata de la valeur, plafonnées par pari ; aucune sous MISE_MIN.

    Le budget n'est pas forcément entièrement dépensé : on ne force pas un pari pour « tout jouer »."""
    if selection.empty:
        return selection.assign(mise=[])
    plafond_total = budget if budget_pertes is None else max(min(budget, budget_pertes), 0)
    poids = selection["valeur"].clip(lower=0.01)
    parts = (poids / poids.sum()).clip(upper=PROFILS_PLAN[profil]["part_max"])
    mises = np.floor(parts * plafond_total / 0.5) * 0.5  # arrondi vers le bas : jamais au-delà du budget
    mises = mises.where(mises >= MISE_MIN, 0.0)
    return selection.assign(mise=mises.astype(float))


def joker(conseils, plan, budget):
    """Joker outsider (option) : meilleur conseil Placé (règle confirmée) sur un cheval de cote Gagnant
    >= COTE_OUTSIDER, dans une course absente du plan ; mise = PART_JOKER du budget.

    Non prouvé : sur 58 conseils passés de ce type, le rendement va de 0 % à +112 % selon la tranche de
    cote, avec des marges d'erreur énormes. Il est suivi à part pour savoir s'il vaut quelque chose."""
    if conseils.empty:
        return None
    pris = set(plan["course"]) if not plan.empty else set()
    cands = conseils[(conseils["regle"] == "confirmée") & (conseils["cote_gagnant"] >= COTE_OUTSIDER)
                     & ~conseils["course"].isin(pris)].sort_values("valeur", ascending=False)
    if cands.empty:
        return None
    mise = round(budget * PART_JOKER / 0.5) * 0.5
    if mise < MISE_MIN:
        mise = MISE_MIN
    return {**cands.iloc[0].to_dict(), "mise": float(mise)}


def composer(conseils, budget, profil, avec_joker=False, budget_pertes=None):
    """Plan complet : (sélection avec mises, joker ou None). Le total ne dépasse jamais le budget,
    ni les pertes encore autorisées : avec le joker, le plan principal reçoit (1 − PART_JOKER) du budget."""
    plafond = budget if budget_pertes is None else max(min(budget, budget_pertes), 0)
    part_principale = plafond * (1 - PART_JOKER) if avec_joker else plafond
    selection = repartir(selectionner(conseils, profil), part_principale, profil)
    jok = joker(conseils, selection, plafond) if avec_joker else None
    if jok and selection["mise"].sum() + jok["mise"] > plafond:
        jok = None  # budget trop petit pour ajouter le joker
    return selection, jok


def texte_plan(plan, budget, profil, vus, jok=None):
    """Résumé (Telegram) du plan du jour."""
    if plan.empty or plan["mise"].sum() == 0:
        return (f"📅 <b>Plan du jour</b> ({profil}, budget {budget:.0f} €)\nAucune course prometteuse parmi "
                f"{vus} courses à venir pour l'instant. Les alertes avant départ restent actives.")
    lignes = [f"📅 <b>Plan du jour</b> ({profil}, budget {budget:.0f} €) — provisoire, à confirmer avant chaque départ"]
    for _, r in plan.iterrows():
        if r["mise"] <= 0:
            continue
        lignes.append(f"• {r['heure']} {r['course']} {r['hippodrome']} : Placé n° <b>{r['num']} {r['nom']}</b> — "
                      f"{r['mise']:.2f} € (cote Placé {r['cote_min']:g}–{r['cote_max']:g}, "
                      f"jouer si ≥ {r['cote_mini_a_jouer']:.2f})")
    if jok:
        lignes.append(f"🃏 Joker outsider (non prouvé) : {jok['heure']} {jok['course']} Placé n° <b>{jok['num']} "
                      f"{jok['nom']}</b> (cote Gagnant {jok['cote_gagnant']:g}) — {jok['mise']:.2f} €")
    total = plan["mise"].sum() + (jok["mise"] if jok else 0)
    lignes.append(f"Total : {total:.2f} € sur {budget:.0f} €. 🧪 Phase de test : à blanc.")
    return "\n".join(lignes)
