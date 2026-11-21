"""Tâche automatique : PMU, Google Sheet et Telegram simulés."""
from datetime import datetime, timedelta
from unittest import mock

import pandas as pd
import pytest

import place
import pmu
import suivi_auto
from test_app import get_course2_terminee
from test_pmu import PROGRAMME, faux_get

HEURE_C2 = pmu.lire_programme(PROGRAMME)[1]["heure"]  # course R1C2, « à venir » dans le faux programme


def instant(minutes_avant_c2):
    h, m = map(int, HEURE_C2.split(":"))
    return datetime(2026, 11, 21, h, m, tzinfo=pmu.PARIS) - timedelta(minutes=minutes_avant_c2)


class FausseFeuille:
    def __init__(self):
        self.valeurs = []

    def get_all_values(self):
        return [list(map(str, l)) for l in self.valeurs]

    def clear(self):
        self.valeurs = []

    def update(self, valeurs, cellule):
        self.valeurs = valeurs


def suivi_vide():
    return pd.DataFrame(columns=place.COLONNES_SUIVI)


def test_releve_les_courses_qui_partent_bientot():
    with mock.patch("requests.get", side_effect=faux_get):
        suivi, messages = suivi_auto.relever_conseils(suivi_vide(), instant(10), 1000, "Équilibré", pause=0)
    confirme = suivi[suivi["regle"] == "confirmée"].iloc[0]
    assert confirme["course"] == "R1C2" and confirme["num"] == "6" and confirme["source"] == "automatique"
    assert any("Placé conseillé" in m and "STINGO" in m for m in messages)
    assert all(r in ("confirmée", "corrigée") for r in suivi["regle"])


@pytest.mark.parametrize("minutes", [1, 30])
def test_ignore_les_courses_trop_proches_ou_trop_lointaines(minutes):
    with mock.patch("requests.get", side_effect=faux_get):
        suivi, messages = suivi_auto.relever_conseils(suivi_vide(), instant(minutes), 1000, "Équilibré", pause=0)
    assert suivi.empty and messages == []


def test_pas_de_doublon():
    with mock.patch("requests.get", side_effect=faux_get):
        suivi, _ = suivi_auto.relever_conseils(suivi_vide(), instant(15), 1000, "Équilibré", pause=0)
        suivi2, messages = suivi_auto.relever_conseils(suivi, instant(5), 1000, "Équilibré", pause=0)
    assert len(suivi2) == len(suivi) and messages == []


def test_reglement_et_bilan():
    with mock.patch("requests.get", side_effect=faux_get):
        suivi, _ = suivi_auto.relever_conseils(suivi_vide(), instant(10), 1000, "Équilibré", pause=0)
    with mock.patch("requests.get", side_effect=get_course2_terminee):
        suivi, regles = suivi_auto.regler_attente(suivi)
    confirme = suivi[suivi["regle"] == "confirmée"].iloc[0]
    assert confirme["resultat"] == "Placé" and confirme["rapport"] == 3.4
    texte = suivi_auto.message_bilan(regles, suivi)
    assert "✅ R1C2 n° 6 STINGO : Placé à 3.40 €" in texte and "Règle confirmée : 1 conseils réglés" in texte


def test_passage_complet_google_sheets_et_telegram(monkeypatch):
    feuille = FausseFeuille()
    monkeypatch.setattr(suivi_auto, "ouvrir_feuille", lambda: feuille)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "JETON-TEST")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(suivi_auto, "datetime", mock.Mock(now=lambda tz=None: instant(10)))
    with mock.patch("requests.get", side_effect=faux_get), mock.patch("requests.post") as post:
        post.return_value.status_code = 200
        assert suivi_auto.main() == 0
    assert feuille.valeurs[0] == place.COLONNES_SUIVI and len(feuille.valeurs) >= 2
    envoi = post.call_args_list[0]
    assert envoi.args[0] == "https://api.telegram.org/botJETON-TEST/sendMessage"
    assert envoi.kwargs["json"]["chat_id"] == "42" and "STINGO" in envoi.kwargs["json"]["text"]

    # Passage suivant, après la course : la feuille est relue, le conseil est réglé
    monkeypatch.setattr(suivi_auto, "datetime", mock.Mock(now=lambda tz=None: instant(-60)))
    with mock.patch("requests.get", side_effect=get_course2_terminee), mock.patch("requests.post") as post:
        post.return_value.status_code = 200
        suivi_auto.main()
    relu = suivi_auto.lire(feuille)
    assert (relu[relu["regle"] == "confirmée"]["resultat"] == "Placé").all()
    assert "Résultats" in post.call_args_list[-1].kwargs["json"]["text"]


def test_passage_a_sec_sans_identifiants(monkeypatch, capsys):
    monkeypatch.delenv("GSHEETS_CREDENTIALS", raising=False)
    monkeypatch.setattr(suivi_auto, "datetime", mock.Mock(now=lambda tz=None: instant(10)))
    with mock.patch("requests.get", side_effect=faux_get), mock.patch("requests.post") as post:
        suivi_auto.main()
    sortie = capsys.readouterr().out
    assert "à sec" in sortie and "STINGO" in sortie and post.call_count == 0
