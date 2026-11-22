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


# --- Discipline et chances -------------------------------------------

def site():
    return tl.extraire_data_pro((DONNEES / "partants_site.txt").read_text())[0]


def test_discipline_detectee():
    assert tl.detecter_discipline(site()) == "Obstacles"
    assert tl.detecter_discipline(tl.extraire_data_pro("1 A 1a 2a Da\n2 B 3m 1a")[0]) == "Trot"
    assert tl.detecter_discipline(tl.extraire_data_pro("1 A\n2 B")[0]) is None


def test_probas_marche():
    m = tl.probas_marche(site())
    assert abs(sum(m.values()) - 1) < 1e-9
    assert max(m, key=m.get) == "5"  # le favori à 1.7
    assert tl.probas_marche(tl.extraire_data_pro("1 A 2.5\n2 B")[0]) is None


def test_comparer_chances():
    t = tl.comparer_chances([{"num": "4", "p": .6}, {"num": "5", "p": .4}], site())
    assert list(t["num"])[:2] == ["4", "5"] and len(t) == 7
    assert abs(t["proba_marche"].sum() - 1) < 1e-9 and set(t.columns) == {"num", "nom", "cote", "proba_ia", "proba_marche"}
    sans = tl.comparer_chances([{"num": "1", "p": 1.0}], tl.extraire_data_pro("1 A 2.5\n2 B 3a")[0])
    assert sans["proba_marche"].isna().all()


def test_valider_reponse():
    df = site()
    res, alertes = tl.valider_reponse({
        "m": "☀️", "chevaux": [{"num": "5", "p": 50, "out": False}, {"num": "4", "p": "30%", "out": True},
                              {"num": "12", "p": 10}, {"num": "7", "p": 20, "out": True}, {"num": "5", "p": 5}],
        }, df)
    assert [c["num"] for c in res["chevaux"]] == ["5", "4", "7"]
    assert abs(sum(c["p"] for c in res["chevaux"]) - 1) < 1e-9  # 50+30+20 = 100 %
    assert [c["out"] for c in res["chevaux"]] == [False, True, False]  # un seul outsider
    assert res["chevaux"][0]["nom"] == "LOKI DE LA BRUNIE"
    assert alertes == ["Gemini a cité le n° 12, qui n'est pas au départ : ignoré."]


def test_reponse_inutilisable():
    for mauvais in [{}, {"chevaux": []}, {"chevaux": [{"num": "99", "p": 10}]}, {"chevaux": "x"}]:
        with pytest.raises(ValueError):
            tl.valider_reponse(mauvais, site())


def test_prompt_sans_conseil_de_pari():
    p = tl.construire_prompt("1 - A (F | 1a)", "Auteuil", "Obstacles", "Soleil, terrain souple")
    assert "Soleil, terrain souple" in p and "CHAQUE partant" in p
    assert "pari_nom" not in p and "mise" not in p.lower().replace("mission", "")
    assert "❔" in tl.construire_prompt("x", "Auteuil", "Obstacles", "AUCUNE DONNÉE")


# --- Pronostics publiés ------------------------------------------------------

CONSULTEES = [{"titre": "paris-turf.com", "url": "https://r/1", "domaine": "paris-turf.com"},
              {"titre": "equidia.fr", "url": "https://r/2", "domaine": "equidia.fr"}]


def test_compiler_pronostics():
    rep = {"sources": [
        {"nom": "Paris-Turf", "site": "https://www.paris-turf.com/pronos", "selection": ["5", "4", "1", "12"]},
        {"nom": "Equidia", "site": "equidia.fr", "selection": ["05", "1", "3", "1"]},
        {"nom": "Inventé", "site": "faux.com", "selection": ["7"]},
        {"nom": "Vide", "site": "equidia.fr", "selection": []},
    ]}
    c = tl.compiler_pronostics(rep, CONSULTEES, site())
    assert [s["nom"] for s in c["sources"]] == ["Paris-Turf", "Equidia"]
    assert c["ecartees"] == 1
    assert c["alertes"] == ["Paris-Turf cite des numéros absents (12) : ignorés."]
    assert [(e["num"], e["points"], e["citations"], e["premier"]) for e in c["consensus"]] == [
        ("5", 10, 2, 2), ("1", 7, 2, 0), ("4", 4, 1, 0), ("3", 3, 1, 0)]
    assert tl.texte_consensus(c).splitlines()[0] == "n° 5 LOKI DE LA BRUNIE : 10 pts, cité par 2/2 sources, 1er choix de 2"


def test_compiler_pronostics_vide_ou_invalide():
    for rep in [None, {}, {"sources": "x"}, {"sources": [{"nom": "A", "site": "a.fr", "selection": ["5"]}]}]:
        c = tl.compiler_pronostics(rep, CONSULTEES, site())
        assert c["sources"] == [] and tl.texte_consensus(c) is None


def test_domaine():
    assert tl._domaine("https://www.Paris-Turf.com/x") == "paris-turf.com"
    assert tl._domaine("Equidia") is None



def test_source_ecrite_autrement_que_le_domaine():
    consultees = [{"titre": d, "url": f"https://r/{d}", "domaine": d}
                  for d in ["frequence-turf.fr", "jeu-legal-france.fr", "canalturf.com", "zeturf.fr"]]
    rep = {"sources": [
        {"nom": "Fréquence Turf", "site": "frequenceturf.fr", "selection": ["5"]},     # tirets oubliés
        {"nom": "Jeu Legal France", "site": "jeulegalfrance.fr", "selection": ["4"]},
        {"nom": "Canalturf", "site": "", "selection": ["1"]},                          # site absent, nom = domaine
        {"nom": "ZETURF", "site": "www.zeturf.fr", "selection": ["3"]},
        {"nom": "Vertex AI Search (Synthèse de dix sources)", "site": "", "selection": ["5"]},  # pas un site
        {"nom": "Turf Inventé", "site": "turfinvente.fr", "selection": ["5"]},
    ]}
    c = tl.compiler_pronostics(rep, consultees, site())
    assert [s["domaine"] for s in c["sources"]] == ["frequence-turf.fr", "jeu-legal-france.fr", "canalturf.com", "zeturf.fr"]
    assert c["ecartees"] == 2



def test_lire_pronostics():
    texte = """Voici les pronostics trouvés :

RueDesJoueurs (experte) | ruedesjoueurs.com | 10-8-12-7-13
**Canalturf** | canalturf.com | 10 - 12 - 9
Ligne sans format
ZETURF | zeturf.com | aucun numéro
"""
    assert tl.lire_pronostics(texte) == {"sources": [
        {"nom": "RueDesJoueurs (experte)", "site": "ruedesjoueurs.com", "selection": ["10", "8", "12", "7", "13"]},
        {"nom": "Canalturf", "site": "canalturf.com", "selection": ["10", "12", "9"]}]}
    assert tl.lire_pronostics("AUCUN") == {"sources": []}
    assert tl.lire_pronostics('{"sources": [{"nom": "A", "site": "a.fr", "selection": ["1"]}]}')["sources"][0]["nom"] == "A"
