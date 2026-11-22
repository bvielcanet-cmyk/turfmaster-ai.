from datetime import datetime
from unittest import mock

import requests

import feux_du_matin


LIGNE = {"feu": "vert", "heure": "14:00", "course": "R1C1", "hippodrome": "A & B", "favori": "n° 1 <X>",
         "victoire": .4}


def test_message_sans_pari_ni_mise():
    t = feux_du_matin.message([LIGNE] * 12, datetime(2026, 11, 22, 10, 17))
    assert "🟢 12" in t and t.count("R1C1") == feux_du_matin.MAX_COURSES and "A &amp; B" in t and "&lt;X&gt;" in t
    assert "€" not in t and "JOUER" not in t.upper() and "Aucun avantage démontré" in t


def test_jeton_jamais_affiche(monkeypatch, capsys):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "JETON-TEST")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    with mock.patch("pmu.programme", return_value=[]), \
            mock.patch("requests.post", side_effect=requests.ConnectionError("botJETON-TEST")):
        assert feux_du_matin.main() == 1
    assert "JETON-TEST" not in capsys.readouterr().out
