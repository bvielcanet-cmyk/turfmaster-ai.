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
    chances = tl.comparer_chances([{"num": "1", "p": .7}, {"num": "2", "p": .3}], df)
    ligne = mesure.ligne_analyse("x", "2026-11-21 12:00", "21112026", "R1C1", "Auteuil", "Plat", chances)
    partants = json.loads(ligne["partants"])
    assert partants["1"]["ia"] == .7 and partants["1"]["cote"] == 2.0 and round(partants["1"]["cotes"], 2) == .6
    assert ligne["decision"] == "Information" and not ligne["mise"] and ligne["gagnant"] == ""


def test_meme_course_remplacee():
    df = mesure.ajouter_analyse(None, analyse("", COTES, COTES, "R1C1", "21112026", ident="a"))
    df = mesure.ajouter_analyse(df, analyse("", COTES, COTES, "R1C1", "21112026", ident="b"))
    df = mesure.ajouter_analyse(df, analyse("", COTES, COTES, "R1C1", "21112026", profil="Prudent", ident="c"))
    df = mesure.ajouter_analyse(df, analyse("", COTES, COTES, ident="d"))
    df = mesure.ajouter_analyse(df, analyse("", COTES, COTES, ident="e"))  # courses collées : jamais remplacées
    assert list(df["id"]) == ["c", "d", "e"]


def test_scores_ia_meilleure():
    # L'IA met toujours le gagnant (n° 3) plus haut que les cotes
    df = pd.DataFrame([analyse("3", {"1": .3, "2": .2, "3": .5}, COTES, ident=str(i)) for i in range(5)]
                      + [analyse("", COTES, COTES, ident="attente")])
    sc = mesure.scores(df)
    assert sc["n"] == 5
    assert sc["log_ia"] < sc["log_cotes"] and sc["brier_ia"] < sc["brier_cotes"]
    assert sc["favori_ia"] == 1 and sc["favori_cotes"] == 0


def test_scores_cotes_meilleures():
    df = pd.DataFrame([analyse("1", {"1": .2, "2": .4, "3": .4}, COTES, ident=str(i)) for i in range(4)])
    sc = mesure.scores(df)
    assert sc["log_cotes"] < sc["log_ia"]


def test_scores_vides_ou_illisibles():
    assert mesure.scores(None) == {"n": 0}
    df = pd.DataFrame([analyse("9", COTES, COTES), {**analyse("1", COTES, COTES), "partants": "pas du json"}])
    assert mesure.scores(df) == {"n": 0}


@pytest.mark.parametrize("valeur, attendu", [(None, ""), (float("nan"), ""), ("nan", ""), (5.0, "5"), (5, "5"),
                                             ("R1C3", "R1C3"), (" 4 ", "4"), (2.5, "2.5")])
def test_texte_cellule(valeur, attendu):
    assert mesure.texte_cellule(valeur) == attendu


def test_en_attente_avec_cellules_vides_relues():
    df = pd.DataFrame({"gagnant": [float("nan"), 5.0, ""]})
    assert list(mesure.en_attente(df).index) == [0, 2]
