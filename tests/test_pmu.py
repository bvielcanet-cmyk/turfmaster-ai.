import json
from pathlib import Path
from unittest import mock

import pytest
import requests

import pmu
import turf_logic as tl

DONNEES = Path(__file__).parent / "donnees"
PROGRAMME = json.loads((DONNEES / "pmu_programme.json").read_text())
PARTICIPANTS = json.loads((DONNEES / "pmu_participants.json").read_text())
RAPPORTS = json.loads((DONNEES / "pmu_rapports.json").read_text())


def faux_get(url, **kw):
    r = mock.Mock(status_code=200)
    r.json.return_value = (PARTICIPANTS if url.endswith("/participants") else
                           RAPPORTS if url.endswith("/rapports-definitifs") else PROGRAMME)
    return r


def test_programme():
    courses = pmu.lire_programme(PROGRAMME)
    c1, c2 = courses
    assert c1["id"] == "R1C1" and c1["hippodrome"] == "Auteuil" and c1["discipline"] == "Obstacles"
    assert c1["statut"] == "terminée" and c1["arrivee"][:3] == ["5", "1", "6"]
    assert c2["statut"] == "à venir" and c2["arrivee"] == []
    assert pmu.libelle_course(c1).startswith("R1C1 · ") and pmu.libelle_course(c1).endswith("— terminée")


def test_partants():
    df = pmu.lire_partants(PARTICIPANTS)
    assert list(df["NUM"]) == ["1", "3", "4", "5", "6", "7"]  # le n° 2, non partant, est exclu
    loki = df[df["NUM"] == "5"].iloc[0]
    assert loki["NOM"] == "LOKI DE LA BRUNIE" and loki["COTE"] == 10.0
    assert loki["Info"] == "F | 3s 2s 6c 2s 2s (25) 2s 2s 2s 2s | H/5 | 66 kg | T.BEAURAIN / B.GOURDON (S) | cote 10"
    assert tl.detecter_discipline(df) == "Obstacles" and tl.probas_marche(df) is not None


def test_rapports_en_euros():
    assert pmu.lire_rapports_gagnant(RAPPORTS) == {"5": 10.4}
    assert pmu.lire_rapports_gagnant([]) == {}


def test_arrivee():
    with mock.patch("requests.get", side_effect=faux_get):
        a = pmu.arrivee("21112026", 1, 1)
        b = pmu.arrivee("21112026", 1, 2)
    assert a == {"terminee": True, "annulee": False, "gagnant": "5", "ordre": ["5", "1", "6", "2", "3", "4"],
                 "rapports_gagnant": {"5": 10.4}}
    assert b["terminee"] is False and b["gagnant"] is None


@pytest.mark.parametrize("effet, message", [
    (requests.ConnectionError(), "injoignable"),
    (mock.Mock(status_code=404), "introuvable"),
    (mock.Mock(status_code=503), "code 503"),
])
def test_erreurs(effet, message):
    kw = {"side_effect": effet} if isinstance(effet, Exception) else {"return_value": effet}
    with mock.patch("requests.get", **kw), pytest.raises(pmu.PmuErreur, match=message):
        pmu.lire_programme(pmu._get("https://x"))


def test_decouper_id():
    assert pmu.decouper_id("R1C3") == (1, 3)
    with pytest.raises(ValueError):
        pmu.decouper_id("")
