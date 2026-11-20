"""Tests de l'interface avec un Gemini et un Google Sheet simulés."""
import json
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
import requests
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
PARTANTS = "12 FAKIR D4 1a 2a 3.5\n4 BOLERO DA 3a\n7 CASTOR 1m\n1 DIAMANT DP 5a\n9 ETOILE 2a"
REPONSE = {
    "m": "☀️", "d": "2700m", "r": "Modéré", "ordre": "12 - 4 - 7",
    "podium": [{"n": "12 - FAKIR", "p": "38%", "out": False}, {"n": "4 - BOLERO", "p": "22%", "out": False},
               {"n": "7 - CASTOR", "p": "15%", "out": True}, {"n": "1 - DIAMANT", "p": "11%", "out": False},
               {"n": "9 - ETOILE", "p": "8%", "out": False}],
    "pari_nom": "Trio", "pari_nums": "12 - 4 - 7", "gain": "+2.50€",
}


def http(code=200, texte=None):
    r = mock.Mock(status_code=code)
    texte = texte if texte is not None else "```json\n" + json.dumps(REPONSE) + "\n```"
    r.json.return_value = {"candidates": [{"content": {"parts": [{"text": texte}]}}]}
    return r


@pytest.fixture(autouse=True)
def vider_cache():
    st.cache_data.clear()


def lancer(reponses=None, exc=None, texte=PARTANTS, secrets=True, sheets=None, profil=None):
    at = AppTest.from_file(APP, default_timeout=30)
    if secrets:
        at.secrets["gemini"] = {"api_key": "CLE-TEST"}
    else:
        # Secrets sans section [gemini] : remplace aussi un éventuel ~/.streamlit/secrets.toml
        at.secrets["autre"] = {"x": 1}
    if sheets is not None:
        at.secrets["connections"] = {"gsheets": {"type": "service_account"}}
    post = mock.patch("requests.post", side_effect=exc or reponses)
    conn = mock.patch("streamlit.connection", return_value=sheets)
    with post as p, conn:
        at.run()
        if profil:
            at.select_slider[0].set_value(profil).run()
        if at.text_area:
            at.text_area[0].input(texte)
            [b for b in at.button if "TICKET" in b.label][0].click().run()
    return at, p


def textes(elements):
    return [e.value for e in elements]


def test_sans_secret():
    at, _ = lancer(secrets=False)
    assert "Configurez votre API KEY" in textes(at.error)[0]


def test_nominal_avec_recherche():
    at, p = lancer([http()])
    assert not at.exception and not at.error
    labels = [m.label for m in at.metric]
    assert "🥉 3ème 🔥 OUT" in labels  # outsider placé où Gemini l'a indiqué
    assert "20.00 €" in textes(at.success)[0]  # 2 % de 1000 €
    url, kwargs = p.call_args.args[0], p.call_args.kwargs
    assert "v1beta" in url and kwargs["json"]["tools"] == [{"google_search": {}}]
    assert kwargs["headers"] == {"x-goog-api-key": "CLE-TEST"}
    assert "CLE-TEST" not in url
    assert "cote 3.5" in kwargs["json"]["contents"][0]["parts"][0]["text"]


def test_profil_prudent():
    at, p = lancer([http()], profil="Prudent")
    assert "10.00 €" in textes(at.success)[0]
    assert "Simple Placé" in p.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"]


def test_recherche_indisponible_bascule_sans():
    at, p = lancer([http(400), http()])
    assert p.call_count == 2 and "tools" not in p.call_args.kwargs["json"]
    assert any("Recherche Google indisponible" in i for i in textes(at.info))
    assert not at.error


@pytest.mark.parametrize("reponses, exc, message", [
    ([http(429), http(429)], None, "Quota Gemini dépassé"),
    (None, requests.Timeout(), "pas répondu à temps"),
    ([http(500)], None, "code 500"),
    ([http(texte="")], None, "vide ou bloquée"),
    ([http(texte="désolé, pas de JSON")], None, "Erreur d'analyse"),
])
def test_erreurs(reponses, exc, message):
    at, _ = lancer(reponses, exc=exc)
    assert not at.exception
    assert message in textes(at.error)[0]


def test_cache_meme_course():
    at, p = lancer([http()])
    with mock.patch("requests.post", side_effect=[http()]) as p2:
        [b for b in at.button if "TICKET" in b.label][0].click().run()
    assert p2.call_count == 0  # réponse reprise du cache


def test_lignes_ignorees_et_saisie_vide():
    at, _ = lancer([http()], texte=PARTANTS + "\n--- divers ---")
    assert "--- divers ---" in textes(at.warning)[0]
    at, p = lancer([], texte="")
    assert "Veuillez saisir des partants" in textes(at.error)[0] and p.call_count == 0


def test_historique_desactive_sans_config():
    at, _ = lancer([http()])
    assert any("Historique désactivé" in i for i in textes(at.info))
    assert not [b for b in at.button if "Enregistrer" in b.label]


def test_enregistrer_ticket_et_stats():
    feuille = mock.Mock()
    feuille.read.side_effect = Exception("onglet absent")
    at, _ = lancer([http()], sheets=feuille)
    with mock.patch("streamlit.connection", return_value=feuille):
        [b for b in at.button if "Enregistrer le ticket" in b.label][0].click().run()
    assert feuille.create.call_count == 1
    ecrit = feuille.create.call_args.kwargs["data"]
    assert ecrit.iloc[0][["pari", "chevaux", "mise", "resultat"]].tolist() == ["Trio", "12 - 4 - 7", 20.0, "En attente"]
    assert any("Ticket enregistré" in s for s in textes(at.success))

    # Historique existant : un gagné, un perdu
    feuille2 = mock.Mock()
    feuille2.read.side_effect = None
    feuille2.read.return_value = pd.DataFrame([
        {"date": "d", "hippodrome": "V", "discipline": "Trot", "profil": "Équilibré", "pari": "Trio",
         "chevaux": "1", "mise": 20, "resultat": "Gagné", "gain_reel": 50},
        {"date": "d", "hippodrome": "V", "discipline": "Trot", "profil": "Équilibré", "pari": "Trio",
         "chevaux": "2", "mise": 20, "resultat": "Perdu", "gain_reel": 0},
    ])
    at, _ = lancer([], texte="", sheets=feuille2)
    valeurs = {m.label: m.value for m in at.metric}
    assert valeurs["Bénéfice"] == "+10.00 €" and valeurs["ROI"] == "+25.0 %"


def test_copier_coller_site_jusqu_a_gemini():
    texte = (Path(__file__).parent / "donnees" / "partants_site.txt").read_text()
    at, p = lancer([http()], texte=texte)
    assert not at.error and not at.warning
    prompt = p.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"]
    assert "5 - LOKI DE LA BRUNIE (F | 3s 2s 6c" in prompt and "Beaurain T. / Gourdon B. | cote 1.7" in prompt
