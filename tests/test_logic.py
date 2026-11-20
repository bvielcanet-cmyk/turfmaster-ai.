import json

import pandas as pd
import pytest

import turf_logic as tl


@pytest.mark.parametrize("ligne, attendu", [
    ("12 FAKIR D4 1a 2a", ("12 - FAKIR", "D4 | 1a 2a", None)),
    ("3 ÉCLAIR DE LUNE DA 1a", ("3 - ÉCLAIR DE LUNE", "DA | 1a", None)),
    ("8 JOE DP 1a 4.5", ("8 - JOE", "DP | 1a | cote 4.5", 4.5)),
    ("1 Fakir 1a 12,5", ("1 - FAKIR", "F | 1a | cote 12.5", 12.5)),
    ("14. JOUR DE FETE (D4) 1a 3m", ("14 - JOUR DE FETE", "D4 | 1a 3m", None)),
    ("6 O'NEILL-STAR 1h 2s", ("6 - O'NEILL-STAR", "F | 1h 2s", None)),
])
def test_lecture_partant(ligne, attendu):
    df, ignorees = tl.extraire_data_pro(ligne)
    assert ignorees == []
    row = df.iloc[0]
    cote = None if pd.isna(row["COTE"]) else row["COTE"]
    assert (row["FULL_ID"], row["Info"], cote) == attendu


def test_lignes_ignorees():
    df, ignorees = tl.extraire_data_pro("12 FAKIR 1a\n--- divers ---\n(12) 5a\n\n7 3a 4a")
    assert list(df["FULL_ID"]) == ["12 - FAKIR"]
    assert ignorees == ["--- divers ---", "(12) 5a", "7 3a 4a"]


@pytest.mark.parametrize("profil, mise", [("Prudent", 10.0), ("Équilibré", 20.0), ("Offensif", 40.0)])
def test_mise(profil, mise):
    assert tl.calculer_mise(1000, profil) == mise


def test_mise_capital_negatif():
    assert tl.calculer_mise(-50, "Offensif") == 0


def test_extraire_json_avec_texte_autour():
    assert tl.extraire_json('Voici :\n```json\n{"a": 1}\n```\nBonne chance') == {"a": 1}
    with pytest.raises(ValueError):
        tl.extraire_json("pas de json")


def _reponse(**extra):
    base = {"podium": [{"n": f"{i} - C{i}", "p": "10%", "out": False} for i in range(1, 8)],
            "pari_nom": "Trio", "pari_nums": "1 - 2 - 3"}
    base.update(extra)
    return base


def test_valider_reponse_limite_a_5_et_un_seul_outsider():
    res = _reponse()
    res["podium"][2]["out"] = True
    res["podium"][3]["out"] = True
    v = tl.valider_reponse(res)
    assert len(v["podium"]) == 5
    assert [p["out"] for p in v["podium"]] == [False, False, True, False, False]
    assert v["m"] == "❔" and v["gain"] == "?"


@pytest.mark.parametrize("res", [{}, {"podium": []}, _reponse(pari_nums=""), {"podium": ["x"], "pari_nom": "a", "pari_nums": "b"}])
def test_valider_reponse_refuse(res):
    with pytest.raises(ValueError):
        tl.valider_reponse(res)


def test_prompt_contient_profil_et_recherche():
    p = tl.construire_prompt("1 - A (F | 1a)", "Vincennes", "Trot", "Prudent", True)
    assert "Simple Placé" in p and "recherche Google" in p
    assert "❔" in tl.construire_prompt("x", "Vincennes", "Trot", "Offensif", False)


def test_stats():
    df = pd.DataFrame([
        {"mise": 20, "resultat": "Gagné", "gain_reel": 50},
        {"mise": 20, "resultat": "Perdu", "gain_reel": 0},
        {"mise": 20, "resultat": "En attente", "gain_reel": 0},
    ])
    s = tl.calculer_stats(df)
    assert s["nb_tickets"] == 3 and s["nb_resolus"] == 2
    assert s["reussite"] == 50
    assert s["benefice"] == 10 and s["roi"] == 25


def test_stats_vide():
    assert tl.calculer_stats(pd.DataFrame(columns=tl.COLONNES_HISTORIQUE))["roi"] == 0
