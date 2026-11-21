import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import place
import pmu

DONNEES = Path(__file__).parent / "donnees"
PARTANTS = pmu.lire_partants(json.loads((DONNEES / "pmu_participants.json").read_text()))
COTES_PLACE = pmu.lire_cotes_place(json.loads((DONNEES / "pmu_place_probables.json").read_text()))


@pytest.mark.parametrize("k", [2, 3])
def test_harville_somme_egale_au_nombre_de_places(k):
    p = np.array([.4, .25, .15, .1, .06, .04])
    probas = place.harville_place(p, k)
    assert probas.sum() == pytest.approx(k)
    assert all(probas[i] >= probas[i + 1] for i in range(len(p) - 1))  # ordre conservé
    assert all(0 < x <= 1 for x in probas)


def test_nombre_places():
    assert place.nombre_places(7) == 2 and place.nombre_places(8) == 3


def test_conseil_sur_vraie_course():
    c = place.conseil_place(PARTANTS, COTES_PLACE, "Équilibré", 1000)
    assert c["num"] == "6" and c["nom"] == "STINGO"
    assert c["cote_min"] == 3.1 and c["cote_max"] == 3.9
    assert c["gain_espere"] == pytest.approx(c["proba"] * 3.1 - 1) and c["gain_espere"] >= .10
    assert c["cote_mini_a_jouer"] == pytest.approx(1.10 / c["proba"], abs=.01)
    assert c["mise"] == 10.0  # 1 % de 1000 € en Équilibré
    assert place.conseil_place(PARTANTS, COTES_PLACE, "Prudent", 1000)["mise"] == 5.0
    assert place.conseil_place(PARTANTS, COTES_PLACE, "Offensif", 1000, budget_restant=4)["mise"] == 4.0


def test_pas_de_conseil():
    assert place.conseil_place(PARTANTS, {}, "Équilibré", 1000) is None  # pas de cotes du Placé
    sans_valeur = {n: (1.1, 1.3) for n in PARTANTS["NUM"]}
    assert place.conseil_place(PARTANTS, sans_valeur, "Équilibré", 1000) is None
    trop_haute = {"6": (25.0, 30.0)}
    assert place.conseil_place(PARTANTS, trop_haute, "Équilibré", 1000) is None  # cote > 20 : hors règle
    sans_cote = PARTANTS.copy()
    sans_cote.loc[0, "COTE"] = None
    assert place.conseil_place(sans_cote, COTES_PLACE, "Équilibré", 1000) is None


def suivi_un(conseil=None, course="R1C2", date_course="21112026"):
    conseil = conseil or place.conseil_place(PARTANTS, COTES_PLACE, "Équilibré", 1000)
    return place.ajouter_suivi(None, place.ligne_suivi("P1", "2026-11-21 12:00", date_course, course, "Auteuil", conseil))


def test_un_seul_conseil_par_course():
    df = suivi_un()
    autre = place.ligne_suivi("P2", "2026-11-21 12:05", "21112026", "R1C2", "Auteuil",
                              place.conseil_place(PARTANTS, COTES_PLACE, "Prudent", 1000))
    df = place.ajouter_suivi(df, autre)
    df = place.ajouter_suivi(df, place.ligne_suivi("P3", "x", "21112026", "R1C3", "Auteuil",
                                                    place.conseil_place(PARTANTS, COTES_PLACE, "Prudent", 1000)))
    assert list(df["id"]) == ["P2", "P3"]


def arrivee(terminee=True, annulee=False, ordre=("6", "1", "5"), place_=None):
    return {"terminee": terminee, "annulee": annulee, "gagnant": ordre[0] if terminee else None,
            "ordre": list(ordre), "rapports_gagnant": {}, "rapports_place": place_ if place_ is not None else {"6": 3.4, "1": 1.8}}


def test_regler():
    df = suivi_un()
    assert not place.regler(df, 0, arrivee(terminee=False))
    assert place.regler(df, 0, arrivee())
    assert df.at[0, "resultat"] == "Placé" and df.at[0, "rapport"] == 3.4 and df.at[0, "gain"] == pytest.approx(24.0)
    df = suivi_un()
    assert place.regler(df, 0, arrivee(ordre=("5", "1", "3"), place_={"5": 4.0, "1": 2.0}))
    assert df.at[0, "resultat"] == "Non placé" and df.at[0, "gain"] == -10.0
    df = suivi_un()
    assert not place.regler(df, 0, arrivee(place_={}))  # placé mais rapports pas encore publiés
    assert place.regler(df, 0, arrivee(annulee=True, terminee=False))
    assert df.at[0, "resultat"] == "Annulée" and df.at[0, "gain"] == 0.0


def test_stats_suivi():
    df = pd.concat([suivi_un(course=f"R1C{i}") for i in range(4)], ignore_index=True)
    place.regler(df, 0, arrivee())                                          # placé à 3.4
    place.regler(df, 1, arrivee(ordre=("5", "1", "3"), place_={"5": 4.0}))  # non placé
    place.regler(df, 2, arrivee(annulee=True, terminee=False))              # annulée : ignorée
    s = place.stats_suivi(df)
    assert s["n"] == 2 and s["en_attente"] == 1 and s["places"] == .5
    assert s["rendement"] == pytest.approx((3.4 + 0) / 2 - 1)
    assert s["gain"] == pytest.approx(24.0 - 10.0)
    assert place.stats_suivi(None) == {"n": 0, "en_attente": 0}
