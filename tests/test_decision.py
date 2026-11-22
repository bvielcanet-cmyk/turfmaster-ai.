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


def test_plafond_des_grands_favoris():
    o = decision.ordre_estime(course(1.1, 2.2, 25, 30, 40, 50, 60, 80))
    vu = decision.chances_affichees(o)
    assert vu["victoire"].max() <= decision.PLAFOND_GAGNE and vu["place"].max() <= decision.PLAFOND_PLACE
    assert vu.iloc[0]["place"] == vu["place"].max()
    offerts = ["SIMPLE_PLACE", "SIMPLE_GAGNANT", "COUPLE_PLACE"]
    assert all(x["chance"] <= decision.PLAFOND_PLACE for x in decision.pronostics(o, offerts))


def test_classement_sans_ex_aequo_du_plafond():
    base = {"pays": "FRA", "statut": "à venir", "reunion": 1, "heure": "14:00", "hippodrome": "H"}
    programme = [{**base, "id": f"R1C{n}", "course": n} for n in (1, 2)]
    lire = lambda jour, r, n: course(1.3 if n == 1 else 1.1, 9, 12, 20, 30, 40, 50, 60)
    with mock.patch("pmu.depart_passe", return_value=False):
        lignes = decision.cribler(date(2026, 11, 22), None, programme, lire)
    assert lignes[0]["place"] == lignes[1]["place"] == decision.PLAFOND_PLACE and lignes[0]["course"] == "R1C2"
    assert len(lignes[0]["arrivee"]) == 5


def test_les_chances_affichees_font_100():
    vu = decision.chances_affichees(decision.ordre_estime(course(1.1, 9, 10, 11)))
    assert vu["victoire"].sum() == pytest.approx(1) and vu["place"].sum() == pytest.approx(2)


def ligne(ident, heure, brut, feu="vert", offerts=(), cote=2.0):
    return {"course": ident, "cote": cote, "heure": heure, "brut": brut, "feu": feu, "offerts": list(offerts),
            "place": brut, "victoire": brut / 2}


def test_choix_du_one_shot():
    lignes = [ligne("A", "14:00", .70), ligne("B", "14:10", .72), ligne("C", "15:00", .60),
              ligne("R", "16:00", .90, "rouge"), ligne("G", "17:00", .80, offerts=["SIMPLE_GAGNANT"])]
    ids = lambda *a: [x["course"] for x in decision.choisir_courses(lignes, *a)]
    assert ids("tranquille") == ["B"]  # ni la rouge, ni celle sans Simple Placé
    assert ids("tranquille", "C") == ["C"]
    assert ids("double") == ["B", "C"]  # A et B sont trop proches pour rejouer les gains
    assert ids("double", "A") == ["A", "C"]
    assert ids("gros") == ["G"]
    assert ids("tranquille", "R") == []
    assert decision.choisir_courses(lignes[:2], "double") == []
    assert decision.choisir_courses([ligne("P", "14:00", .9, cote=1.1)], "tranquille") == []  # rien à gagner


def test_ticket():
    a, b = ligne("A", "14:00", .7), ligne("B", "15:00", .6)
    t = decision.ticket("double", [a, b], 50, [1.2, 1.5])
    assert t["chance"] == pytest.approx(.42) and t["gain"] == pytest.approx(40) and not t["habituel"]
    assert [e["mise"] for e in t["etapes"]] == pytest.approx([50, 60])
    t = decision.ticket("tranquille", [a], 20, [None])
    assert t["habituel"] and t["gain"] == pytest.approx(6) and t["montant"] == 20
    assert decision.ticket("gros", [a], 20, [3.0])["chance"] == pytest.approx(.35)
    assert decision.ticket("double", [a], 20, [1.2]) is None


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
