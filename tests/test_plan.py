from datetime import datetime

import pandas as pd
import pytest

import plan
import pmu
from test_pmu import PARTICIPANTS, PLACE_PROBABLES, PROGRAMME

COURSES = pmu.lire_programme(PROGRAMME)
PARTANTS = pmu.lire_partants(PARTICIPANTS)
COTES = pmu.lire_cotes_place(PLACE_PROBABLES)


def conseils_types():
    """Trois courses fictives aux conseils de valeurs différentes, plus un outsider."""
    lignes = []
    # (chances de placé corrigées, cote Placé mini, cote Gagnant, règle) ; valeur = chances × cote − 1
    for i, (proba, cote_min, cote_g, regle) in enumerate([(.50, 2.6, 3.0, "confirmée"), (.40, 3.0, 5.0, "confirmée"),
                                                          (.60, 1.85, 2.0, "confirmée"), (.30, 5.0, 12.0, "confirmée"),
                                                          (.35, 3.6, 6.0, "corrigée")]):
        valeur = proba * cote_min - 1
        lignes.append({"course": f"R1C{i + 1}", "heure": f"1{i}:00", "hippodrome": "Auteuil", "discipline": "Plat",
                       "libelle": "x", "regle": regle, "num": str(i + 1), "nom": f"CHEVAL {i}", "cote_min": cote_min,
                       "cote_max": 3.0, "cote_mini_a_jouer": 1.8, "proba_corrigee": proba, "gain_regle": .2,
                       "valeur": valeur, "cote_gagnant": cote_g, "reunion": 1, "numero": i + 1})
    return pd.DataFrame(lignes)


def test_crible_ne_garde_que_les_courses_jouables():
    c2 = COURSES[1]
    h, m = map(int, c2["heure"].split(":"))
    avant = datetime(2026, 11, 21, h, m, tzinfo=pmu.PARIS)
    conseils, vus = plan.cribler(avant.date(), avant.replace(hour=h - 1), programme=COURSES, pause=0,
                                 lire_partants=lambda *a: PARTANTS, lire_cotes=lambda *a: COTES)
    assert vus == 1  # R1C1 est terminée
    assert set(conseils["course"]) == {"R1C2"} and "6" in set(conseils["num"])
    assert conseils.iloc[0]["cote_gagnant"] == 5.2
    trop_tard, vus = plan.cribler(avant.date(), avant.replace(minute=max(m - 2, 0)) if m >= 2 else avant,
                                  programme=COURSES, pause=0, lire_partants=lambda *a: PARTANTS,
                                  lire_cotes=lambda *a: COTES)
    assert vus == 0  # part dans moins de 5 minutes


@pytest.mark.parametrize("profil, attendu", [
    ("Prudent", ["R1C1", "R1C3"]),               # chances corrigées >= 45 %
    ("Équilibré", ["R1C1", "R1C2", "R1C3"]),     # règle confirmée, outsider R1C4 exclu, classement Kelly
    ("Offensif", ["R1C1", "R1C5", "R1C2"]),      # + règle corrigée
])
def test_selection_par_profil(profil, attendu):
    assert list(plan.selectionner(conseils_types(), profil)["course"]) == attendu


def test_repartition():
    sel = plan.selectionner(conseils_types(), "Équilibré")
    r = plan.repartir(sel, 50, "Équilibré")
    assert r["mise"].sum() <= 50 and all(m % 0.5 == 0 for m in r["mise"])
    assert r["mise"].sum() > 0
    assert plan.repartir(sel.head(1), 50, "Équilibré")["mise"].iloc[0] == 25.0  # 50 % max par pari
    assert plan.repartir(sel, 50, "Équilibré", budget_pertes=10)["mise"].sum() <= 10
    assert (plan.repartir(sel, 3, "Équilibré")["mise"] == 0).all()  # sous la mise minimale : pas de pari


def test_joker():
    conseils = conseils_types()
    sel = plan.repartir(plan.selectionner(conseils, "Prudent"), 50, "Prudent")
    j = plan.joker(conseils, sel, 50)
    assert j["course"] == "R1C4" and j["cote_gagnant"] == 12.0 and j["mise"] == 5.0  # 10 % de 50 €
    sans_outsider = conseils[conseils["cote_gagnant"] < 8]
    assert plan.joker(sans_outsider, sel, 50) is None
    assert plan.joker(conseils, sel, 20)["mise"] == plan.MISE_MIN


def test_texte_plan():
    conseils = conseils_types()
    sel = plan.repartir(plan.selectionner(conseils, "Prudent"), 50, "Prudent")
    texte = plan.texte_plan(sel, 50, "Prudent", 12, plan.joker(conseils, sel, 50))
    assert "Plan du jour" in texte and "CHEVAL 2" in texte and "Joker outsider" in texte and "à blanc" in texte
    vide = plan.texte_plan(sel.iloc[0:0].assign(mise=[]), 50, "Prudent", 12)
    assert "Aucune course prometteuse parmi 12" in vide



def test_outsider_jamais_dans_le_plan_principal():
    conseils = conseils_types()
    for profil in plan.PROFILS_PLAN:
        assert (plan.selectionner(conseils, profil)["cote_gagnant"] < plan.COTE_OUTSIDER).all()


def test_croissance():
    assert plan.croissance(.5, 2.6) > plan.croissance(.4, 3.0) > 0
    assert plan.croissance(.3, 3.0) < 0  # sans valeur



@pytest.mark.parametrize("budget", [20, 35, 50, 100])
@pytest.mark.parametrize("profil", list(plan.PROFILS_PLAN))
def test_jamais_au_dela_du_budget(budget, profil):
    sel, jok = plan.composer(conseils_types(), budget, profil, avec_joker=True)
    assert sel["mise"].sum() + (jok["mise"] if jok else 0) <= budget
    sel, jok = plan.composer(conseils_types(), budget, profil, avec_joker=True, budget_pertes=12)
    assert sel["mise"].sum() + (jok["mise"] if jok else 0) <= 12



# --- One shot ------------------------------------------------------------------------------------

def test_chances_calculees():
    perte, gain = plan.chances_calculees([.5, .5], [3.0, 3.0], [.5, .5])
    assert perte == pytest.approx(.25) and gain == pytest.approx(.75)  # un seul gagnant suffit (1,5 > 1)
    perte, gain = plan.chances_calculees([.5, .5], [1.5, 1.5], [.5, .5])
    assert gain == pytest.approx(.25)  # il faut les deux


def test_repartition_optimale_mise_plus_sur_le_plus_sur():
    parts = plan.repartition_optimale([.7, .3], [1.6, 4.0])
    assert parts.sum() == pytest.approx(1) and parts[0] > parts[1]
    assert plan.chances_calculees([.7, .3], [1.6, 4.0], parts)[1] >= plan.chances_calculees([.7, .3], [1.6, 4.0], [.5, .5])[1]


@pytest.mark.parametrize("profil, n", [("Prudent", 2), ("Équilibré", 3), ("Offensif", 2)])
def test_one_shot(profil, n):
    paris, bilan = plan.one_shot(conseils_types(), 50, profil)
    assert bilan["n"] == len(paris) == n
    assert paris["mise"].sum() <= 50 and (paris["mise"] >= plan.MISE_MIN).all()
    assert bilan["feu"] in ("vert", "orange", "rouge")
    assert 0 < bilan["risque_tout_perdre"] <= 1


def test_one_shot_rouge():
    seul = conseils_types().head(1)
    paris, bilan = plan.one_shot(seul, 50, "Équilibré")
    assert bilan["feu"] == "rouge" and "moins de 2" in bilan["raison"]
    paris, bilan = plan.one_shot(conseils_types(), 3, "Équilibré")  # budget trop petit pour 2 mises de 2 €
    assert bilan["feu"] == "rouge"


def test_feu_selon_le_risque():
    c = conseils_types()
    surs = c.assign(proba_corrigee=.8, cote_min=1.5, valeur=.2)
    risques = c.assign(proba_corrigee=.2, cote_min=6.0, valeur=.2)
    assert plan.one_shot(surs, 50, "Équilibré")[1]["feu"] == "vert"
    assert plan.one_shot(risques, 50, "Équilibré")[1]["feu"] == "rouge"
