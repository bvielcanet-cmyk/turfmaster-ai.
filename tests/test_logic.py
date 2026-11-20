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


DONNEES = __import__("pathlib").Path(__file__).parent / "donnees"


def test_copier_coller_site():
    df, ignorees = tl.extraire_data_pro((DONNEES / "partants_site.txt").read_text())
    assert ignorees == []
    assert list(df["FULL_ID"]) == ["1 - ISISDELAGARDE", "2 - FENOMENE D'OC", "3 - CHUCK BERRY",
                                   "4 - FOREST DU PECOS", "5 - LOKI DE LA BRUNIE", "6 - STINGO", "7 - SHERKARA"]
    assert list(df["COTE"]) == [6.5, 53.6, 8.5, 5.8, 1.7, 11.3, 31.5]
    assert df.iloc[0]["Info"] == ("F | 2s 5s 1s (25) 3s 2s 2s 2s 3s 3s (24) 4s 2s 2s | H/8 | 69 kg "
                                  "| Zuliani L. / Lagarde F. | cote 6.5")
    assert "Ts" in df.iloc[1]["Info"] and "F/5" in df.iloc[6]["Info"]


def test_copier_coller_poids_decimal_et_sans_cote():
    df, _ = tl.extraire_data_pro("3\nBOLERO\nDupont A. - Martin B.\nH/6  64,5 kg  1s 2s")
    row = df.iloc[0]
    assert pd.isna(row["COTE"]) and "64,5 kg" in row["Info"]


def test_copier_coller_texte_avant_et_fiche_sans_nom():
    df, ignorees = tl.extraire_data_pro("Prix de Paris\n1\nFAKIR\nH/5 1s 3.2\n2\n\n3\nCASTOR\n2s")
    assert list(df["FULL_ID"]) == ["1 - FAKIR", "3 - CASTOR"]
    assert ignorees == ["Prix de Paris", "N° 2 (nom introuvable)"]
