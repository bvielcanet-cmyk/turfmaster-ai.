import pandas as pd
import pytest

import protection


def test_etat_sans_baisse():
    e = protection.etat(1000, [10, -10, 25])
    assert e["capital"] == 1025 and e["pic"] == 1025 and not e["reduit"] and e["facteur"] == 1.0


def test_reduction_apres_15_pour_cent_puis_retour():
    e = protection.etat(1000, [200, -190])          # pic 1200, capital 1010 : -15,8 %
    assert e["reduit"] and e["facteur"] == 0.5 and e["baisse"] == pytest.approx(1 - 1010 / 1200)
    e = protection.etat(1000, [200, -170])          # 1030 : -14,2 %, pas encore
    assert not e["reduit"]
    e = protection.etat(1000, [200, -190, 30])      # remonte à 1040 : -13 % -> mises normales
    assert not e["reduit"]


def tickets(*lignes):
    return pd.DataFrame([{"date": d, "resultat": r, "mise": m, "gain_reel": g} for d, r, m, g in lignes])


def test_source_tickets_prioritaire():
    t = tickets(("2026-11-02 10:00", "Perdu", 20, 0), ("2026-11-01 10:00", "Gagné", 10, 40),
                ("2026-11-03 10:00", "En attente", 50, 0))
    suivi = pd.DataFrame([{"date": "2026-11-01", "resultat": "Placé", "regle": "confirmée", "gain": 999}])
    e = protection.etat_courant(100, t, suivi)
    assert e["source"] == "tickets joués" and e["capital"] == 100 + 30 - 20 and e["pic"] == 130


def test_source_suivi_si_aucun_ticket():
    suivi = pd.DataFrame([
        {"date": "2026-11-01", "resultat": "Placé", "regle": "confirmée", "gain": 20},
        {"date": "2026-11-02", "resultat": "Non placé", "regle": "confirmée", "gain": -10},
        {"date": "2026-11-02", "resultat": "Placé", "regle": "corrigée", "gain": 500},   # règle en essai : ignorée
        {"date": "2026-11-03", "resultat": "En attente", "regle": "confirmée", "gain": 0},
    ])
    e = protection.etat_courant(100, tickets(), suivi)
    assert e["source"] == "suivi à blanc (fictif)" and e["capital"] == 110 and e["pic"] == 120
    assert protection.etat_courant(100, None, None)["capital"] == 100
