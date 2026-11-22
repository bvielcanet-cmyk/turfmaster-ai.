from datetime import date
from unittest import mock

import pandas as pd
import pytest

import decision
import pmu


def course(*cotes):
    return pd.DataFrame([{"NUM": str(i + 1), "NOM": f"C{i + 1}", "COTE": c} for i, c in enumerate(cotes)])


def test_chances_coherentes():
    o = decision.ordre_estime(course(8, 2, 5, 10, 12, 15, 20, 30))
    assert list(o["num"])[:3] == ["2", "3", "1"] and list(o["rang"]) == list(range(1, 9))
    assert o["victoire"].sum() == pytest.approx(1) and o["place"].sum() == pytest.approx(3)
    assert (o["place"] >= o["victoire"]).all()
    desordre, exact = decision.chances_trio(o)
    assert 0 < exact < desordre < 1
    sept = decision.ordre_estime(course(*[5] * 7))
    assert sept["place"].sum() == pytest.approx(2) and decision.chances_trio(sept) is None


@pytest.mark.parametrize("cotes", [(2, 3, 4), (2, 3, None, 5), (2, 3, 0, 5)])
def test_pas_de_feu_sans_donnees(cotes):
    o = decision.ordre_estime(course(*cotes))
    assert o.empty and decision.feu(o) is None


@pytest.mark.parametrize("victoire, couleur", [(.35, "vert"), (.349, "orange"), (.22, "orange"), (.219, "rouge")])
def test_feu(victoire, couleur):
    assert decision.feu(pd.DataFrame([{"victoire": victoire}])) == couleur


def test_risque_jamais_presente_comme_un_avantage():
    r = decision.risque_pari(.25, 3.0, 10)
    assert r == {"perte": 10.0, "risque": .75, "gain": 20.0, "cout_moyen": 2.5}
    assert decision.risque_pari(.5, 3.0, 10)["cout_moyen"] is None


def test_cribler():
    base = {"pays": "FRA", "statut": "à venir", "reunion": 1, "heure": "14:00", "hippodrome": "H"}
    programme = [{**base, "id": "R1C1", "course": 1}, {**base, "id": "R1C2", "course": 2},
                 {**base, "id": "R1C3", "course": 3, "statut": "terminée"},
                 {**base, "id": "R1C4", "course": 4, "pays": "SWE"}, {**base, "id": "R1C5", "course": 5}]

    def lire(jour, reunion, n):
        if n == 5:
            raise pmu.PmuErreur("panne")
        return course(5, 5, 5, 5, 5) if n == 1 else course(1.4, 8, 9, 12, 20)
    with mock.patch("pmu.depart_passe", return_value=False):
        lignes = decision.cribler(date(2026, 11, 22), None, programme, lire)
    assert [(x["course"], x["feu"]) for x in lignes] == [("R1C2", "vert"), ("R1C1", "rouge")]
