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


@pytest.mark.parametrize("couleur, budget, deja, nombre, mise", [
    ("vert", 20, 0, 0, 2), ("vert", 60, 0, 0, 6), ("orange", 100, 0, 0, 5), ("vert", 5000, 0, 0, 10),
    ("rouge", 100, 0, 0, 0), ("vert", 20, 19, 0, 0), ("vert", 60, 56.7, 0, 3), ("vert", 60, 0, 3, 0),
])
def test_mise_conseillee(couleur, budget, deja, nombre, mise):
    assert decision.mise_conseillee(couleur, budget, deja, nombre) == mise


@pytest.mark.parametrize("budget", range(0, 130, 7))
def test_repartition_dans_le_budget(budget):
    lignes = [{"feu": f, "offerts": []} for f in ("vert", "rouge", "orange", "vert", "vert", "orange")]
    mises = [x["mise"] for x in decision.repartir(lignes, budget, 4)]
    assert sum(mises) <= max(budget - 4, 0) and sum(m > 0 for m in mises) <= 3 and mises[1] == 0


def test_chance_selection_egale_au_podium():
    p = decision.ordre_estime(course(2, 3, 5, 8, 10, 12, 15, 20, 30, 40))["victoire"]
    issues = decision.podiums(p, 3)
    assert decision.chance_selection(p, 2, 3) == pytest.approx(sum(v for i, v in issues.items() if {0, 1} <= set(i)))
    assert decision.chance_selection(p, 3, 3) == pytest.approx(sum(v for i, v in issues.items() if set(i) == {0, 1, 2}))
    assert decision.chance_selection(p, 10, 4) == pytest.approx(1)
    assert decision.chance_selection(p.iloc[:4], 2, 4) == pytest.approx(1)


def test_pronostics_au_dessus_de_30_et_seulement_les_paris_offerts():
    o = decision.ordre_estime(course(1.4, 4, 9, 14, 20, 25, 30, 40, 50, 60))
    offerts = ["SIMPLE_PLACE", "COUPLE_PLACE", "MINI_MULTI"]
    liste = decision.pronostics(o, offerts)
    assert liste and all(x["chance"] > .30 and x["code"] in offerts for x in liste)
    assert [x["chance"] for x in liste] == sorted((x["chance"] for x in liste), reverse=True)
    assert {x["code"] for x in decision.pronostics(o)} <= {"SIMPLE_PLACE", "SIMPLE_GAGNANT"}


def test_favori_corrige_vers_le_bas():
    o = decision.ordre_estime(course(1.4, 8, 9, 12, 20, 25, 30, 40))
    gagne, place = decision.chances_favori(o)
    assert gagne < o.iloc[0]["victoire"] and place < o.iloc[0]["place"]


def test_conseil():
    claire = decision.ordre_estime(course(1.4, 8, 9, 12, 20))
    c = decision.conseiller(claire, 20, 0)
    assert c["num"] == "1" and c["mise"] == 2 and c["cout"] > 0
    assert decision.conseiller(claire, 20, 0, offerts=["SIMPLE_GAGNANT"])["mise"] == 0
    ouverte = decision.ordre_estime(course(5, 5, 5, 5, 5))
    assert decision.conseiller(ouverte, 100, 0)["mise"] == 0


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
