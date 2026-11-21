import json

import pandas as pd
import pytest

import mesure
import turf_logic as tl


def analyse(gagnant, ia, cotes, course="", date_course="", profil="Équilibré", ident="a"):
    partants = {n: {"nom": f"CHEVAL {n}", "ia": ia[n], "cotes": cotes[n], "cote": round(1 / cotes[n], 1)} for n in ia}
    return {"id": ident, "date": "2026-11-21 12:00", "date_course": date_course, "course": course,
            "hippodrome": "Auteuil", "discipline": "Obstacles", "profil": profil,
            "partants": json.dumps(partants), "decision": "Pas de pari", "pari_num": "", "mise": 0.0,
            "gagnant": gagnant, "source_resultat": ""}


COTES = {"1": .5, "2": .3, "3": .2}


def test_ligne_analyse():
    df = pd.DataFrame([{"NUM": "1", "NOM": "A", "COTE": 2.0}, {"NUM": "2", "NOM": "B", "COTE": 3.0}])
    decision = tl.evaluer_pari([{"num": "1", "p": .7}, {"num": "2", "p": .3}], df, 1000, "Offensif")
    ligne = mesure.ligne_analyse("x", "2026-11-21 12:00", "21112026", "R1C1", "Auteuil", "Plat", "Offensif", decision)
    partants = json.loads(ligne["partants"])
    assert partants["1"]["ia"] == .7 and partants["1"]["cote"] == 2.0 and round(partants["1"]["cotes"], 2) == .6
    assert ligne["decision"] == ("Jouer n° 1" if decision["jouer"] else "Pas de pari") and ligne["gagnant"] == ""


def test_meme_course_remplacee():
    df = mesure.ajouter_analyse(None, analyse("", COTES, COTES, "R1C1", "21112026", ident="a"))
    df = mesure.ajouter_analyse(df, analyse("", COTES, COTES, "R1C1", "21112026", ident="b"))
    df = mesure.ajouter_analyse(df, analyse("", COTES, COTES, "R1C1", "21112026", profil="Prudent", ident="c"))
    df = mesure.ajouter_analyse(df, analyse("", COTES, COTES, ident="d"))
    df = mesure.ajouter_analyse(df, analyse("", COTES, COTES, ident="e"))  # courses collées : jamais remplacées
    assert list(df["id"]) == ["b", "c", "d", "e"]


def test_scores_ia_meilleure():
    # L'IA met toujours le gagnant (n° 3) plus haut que les cotes
    df = pd.DataFrame([analyse("3", {"1": .3, "2": .2, "3": .5}, COTES, ident=str(i)) for i in range(5)]
                      + [analyse("", COTES, COTES, ident="attente")])
    sc = mesure.scores(df)
    assert sc["n"] == 5
    assert sc["log_ia"] < sc["log_cotes"] and sc["brier_ia"] < sc["brier_cotes"]
    assert sc["favori_ia"] == 1 and sc["favori_cotes"] == 0
    assert sc["meilleur_poids"] == 1.0


def test_scores_cotes_meilleures():
    df = pd.DataFrame([analyse("1", {"1": .2, "2": .4, "3": .4}, COTES, ident=str(i)) for i in range(4)])
    sc = mesure.scores(df)
    assert sc["log_cotes"] < sc["log_ia"] and sc["meilleur_poids"] == 0.0


def test_scores_vides_ou_illisibles():
    assert mesure.scores(None) == {"n": 0}
    df = pd.DataFrame([analyse("9", COTES, COTES), {**analyse("1", COTES, COTES), "partants": "pas du json"}])
    assert mesure.scores(df) == {"n": 0}


def test_confiance_seulement_avec_assez_de_courses():
    peu = {"n": 10, "meilleur_poids": .2}
    assert mesure.confiance_ia(peu, .5) == (.5, False)
    assez = {"n": mesure.MINIMUM_COURSES, "meilleur_poids": .2}
    assert mesure.confiance_ia(assez, .5) == (.2, True)


def ticket(analyse_id, chevaux="5", mise=10.0, cote=6.0, resultat="En attente"):
    return {"analyse": analyse_id, "chevaux": chevaux, "mise": mise, "cote": cote, "resultat": resultat,
            "gain_reel": 0.0, "source_gain": ""}


def test_mettre_a_jour_tickets():
    analyses = pd.DataFrame([
        {**analyse("5", COTES, COTES, ident="pmu"), "source_resultat": "PMU officiel : 10.4"},
        {**analyse("5", COTES, COTES, ident="gemini"), "source_resultat": "recherche Gemini (non officiel)"},
        {**analyse("3", COTES, COTES, ident="perdu")},
        {**analyse("annulée", COTES, COTES, ident="annulee")},
        {**analyse("", COTES, COTES, ident="attente")},
    ])
    tickets = pd.DataFrame([ticket("pmu"), ticket("gemini"), ticket("perdu"), ticket("annulee"), ticket("attente"),
                            ticket("pmu", resultat="Perdu")])
    maj, n = mesure.mettre_a_jour_tickets(tickets, analyses)
    assert n == 4
    assert maj["resultat"].tolist() == ["Gagné", "Gagné", "Perdu", "Gagné", "En attente", "Perdu"]
    assert maj["gain_reel"].tolist() == [104.0, 60.0, 0.0, 10.0, 0.0, 0.0]
    assert maj["source_gain"].tolist()[:2] == ["rapport officiel PMU", "estimé (cote au moment du pari)"]
