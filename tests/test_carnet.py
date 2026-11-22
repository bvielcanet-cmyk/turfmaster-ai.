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


def test_budget_un_gain_ne_l_agrandit_pas():
    t = pd.concat([paris()] * 4, ignore_index=True)
    t["resultat"] = ["Gagné", "Perdu", "Remboursé", "En attente"]
    t["gain_reel"] = [90.0, 0, 10, 0]
    assert carnet.mise_semaine(t, pd.Timestamp("2026-11-22 12:00")) == 30
    assert carnet.mise_semaine(t, pd.Timestamp("2026-11-30 12:00")) == 0
    assert carnet.bilan(t) == {"n": 2, "attente": 1, "gagnes": 1, "mise": 20, "rendu": 90, "net": 70}
