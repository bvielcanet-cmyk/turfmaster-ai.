import pandas as pd
import pytest

import carnet


def arrivee(**k):
    return {"terminee": True, "annulee": False, "non_partants": ["2"], "rapports_gagnant": {"5": 10.4},
            "rapports_place": {"5": 4.3, "1": 2.0}, **k}


def paris(pari="Simple Gagnant", num="5"):
    return pd.DataFrame([carnet.ligne("2026-11-21 12:00", "21112026", "R1C1", "Auteuil", "Obstacles", pari, num, 8, 10)])


@pytest.mark.parametrize("pari, num, arr, resultat, rendu", [
    ("Simple Gagnant", "5", arrivee(), "Gagné", 104),
    ("Simple Gagnant", "1", arrivee(), "Perdu", 0),
    ("Simple Placé", "1", arrivee(), "Gagné", 20),
    ("Simple Placé", "2", arrivee(), "Remboursé", 10),
    ("Simple Gagnant", "4", arrivee(terminee=False, annulee=True), "Remboursé", 10),
])
def test_regler(pari, num, arr, resultat, rendu):
    df = paris(pari, num)
    assert carnet.regler(df, 0, arr)
    assert df.at[0, "resultat"] == resultat and df.at[0, "gain_reel"] == pytest.approx(rendu)


@pytest.mark.parametrize("arr", [arrivee(terminee=False), arrivee(rapports_gagnant={})])
def test_jamais_de_gain_estime(arr):
    df = paris()
    assert not carnet.regler(df, 0, arr) and df.at[0, "resultat"] == "En attente"


@pytest.mark.parametrize("premiere, seconde, resultat, rendu", [
    (arrivee(), arrivee(), "Gagné", 86),
    (arrivee(rapports_place={"9": 2.0}), None, "Perdu", 0),
    (arrivee(non_partants=["5"]), arrivee(), "Gagné", 20),
    (arrivee(annulee=True), arrivee(annulee=True), "Remboursé", 10),
    (arrivee(), arrivee(terminee=False), "En attente", 0),
])
def test_regler_un_double(premiere, seconde, resultat, rendu):
    df = pd.DataFrame([carnet.ligne("2026-11-21 12:00", "21112026", "R1C1 > R1C4", "A > A", "", "Doublé Placé",
                                    "5 > 1", 1.2, 10)])
    lues = {"R1C1": premiere, "R1C4": seconde}

    def lire(course):
        assert lues[course] is not None, "la 2e course ne doit pas être lue si la 1re est perdue"
        return lues[course]
    assert carnet.regler_double(df, 0, lire) == (resultat != "En attente")
    assert df.at[0, "resultat"] == resultat and df.at[0, "gain_reel"] == pytest.approx(rendu)


def test_budget_un_gain_ne_l_agrandit_pas():
    t = pd.concat([paris()] * 4, ignore_index=True)
    t["resultat"] = ["Gagné", "Perdu", "Remboursé", "En attente"]
    t["gain_reel"] = [90.0, 0, 10, 0]
    assert carnet.mise_semaine(t, pd.Timestamp("2026-11-22 12:00")) == 30
    assert carnet.mise_semaine(t, pd.Timestamp("2026-11-30 12:00")) == 0
    assert carnet.nombre_du_jour(t, pd.Timestamp("2026-11-21").date()) == 3
    assert carnet.bilan(t) == {"n": 2, "attente": 1, "gagnes": 1, "mise": 20, "rendu": 90, "net": 70}
