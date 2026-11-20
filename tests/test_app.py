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
SITE = (Path(__file__).parent / "donnees" / "partants_site.txt").read_text()

# L'IA voit le n° 4 (cote 5.8) nettement au-dessus des cotes : pari mesurable en Équilibré
AVEC_VALEUR = {"m": "☀️", "d": "3500m", "r": "Modéré",
               "chevaux": [{"num": n, "p": p, "out": n == "6"} for n, p in
                           [("5", 45), ("4", 25), ("1", 12), ("3", 8), ("6", 5), ("7", 3), ("2", 2)]],
               "pari_nom": "Trio", "pari_nums": "5 - 4 - 1"}
# L'IA reprend l'avis des cotes : aucune valeur
SANS_VALEUR = {**AVEC_VALEUR, "chevaux": [{"num": n, "p": p} for n, p in
                                          [("5", 50), ("4", 15), ("1", 13), ("3", 10), ("6", 8), ("7", 2), ("2", 2)]]}


def http(code=200, texte=None, json_=AVEC_VALEUR):
    r = mock.Mock(status_code=code)
    texte = texte if texte is not None else json.dumps(json_)
    r.json.return_value = {"candidates": [{"content": {"parts": [{"text": texte}]}}]}
    return r


CONTEXTE = http(texte="Météo : soleil. Terrain : souple. Prix X : 3500 m.")


def http_presse(sources, consultees=("paris-turf.com", "equidia.fr", "geny.com")):
    """Réponse de la recherche de pronostics, avec les pages réellement consultées."""
    r = http(json_={"sources": sources})
    r.json.return_value["candidates"][0]["groundingMetadata"] = {
        "groundingChunks": [{"web": {"uri": f"https://redirect.example/{d}", "title": d}} for d in consultees]}
    return r


PRESSE = http_presse([
    {"nom": "Paris-Turf", "site": "paris-turf.com", "selection": ["5", "4", "1", "3", "6"]},
    {"nom": "Equidia", "site": "www.equidia.fr", "selection": ["4", "5", "3"]},
    {"nom": "Geny", "site": "geny.com", "selection": ["5", "1", "4", "15"]},
    {"nom": "Site inventé", "site": "pronos-inventes.fr", "selection": ["7", "2"]},
])


def gemini_simule(analyses, contexte=CONTEXTE, presse=PRESSE):
    """Faux Gemini qui répond selon la demande (les recherches tournent en parallèle)."""
    file = list(analyses)

    def post(url, json=None, **kw):
        if "tools" in json:
            reponse = presse if "PRONOSTICS" in json["contents"][0]["parts"][0]["text"] else contexte
        else:
            if not file:
                raise AssertionError("analyse Gemini inattendue")
            reponse = file.pop(0)
        if isinstance(reponse, Exception):
            raise reponse
        return reponse
    return post


@pytest.fixture(autouse=True)
def vider_cache():
    st.cache_data.clear()
    st.cache_resource.clear()


def lancer(reponses=None, exc=None, texte=SITE, secrets=True, sheets=None, profil=None,
           recherche=True, discipline=None, limite=None, contexte=CONTEXTE, presse=None):
    at = AppTest.from_file(APP, default_timeout=30)
    if secrets:
        at.secrets["gemini"] = {"api_key": "CLE-TEST"}
    else:
        # Secrets sans section [gemini] : remplace aussi un éventuel ~/.streamlit/secrets.toml
        at.secrets["autre"] = {"x": 1}
    if sheets is not None:
        at.secrets["connections"] = {"gsheets": {"type": "service_account"}}
    effet = exc or gemini_simule(reponses or [], contexte, presse)
    with mock.patch("requests.post", side_effect=effet) as p, \
            mock.patch("streamlit.connection", return_value=sheets):
        at.run()
        if at.text_area:
            if profil:
                at.select_slider[0].set_value(profil)
            if not recherche:
                at.toggle[0].set_value(False)
            if presse is None:
                at.toggle[1].set_value(False)  # pronostics de la presse désactivés par défaut dans les tests
            if discipline:
                at.selectbox[0].set_value(discipline)
            if limite is not None:
                at.number_input[1].set_value(limite)
            at.text_area[0].input(texte)
            analyser(at).click().run()
    return at, p


def analyser(at):
    return [b for b in at.button if "ANALYSER" in b.label][0]


def textes(elements):
    return [e.value for e in elements]


def verdict(at):
    """Texte de l'encadré du verdict (À JOUER / NE PAS JOUER)."""
    return " ".join(m.value for m in at.markdown if "tm-verdict" in m.value)


def classement(at):
    return " ".join(m.value for m in at.markdown if "tm-ligne" in m.value)


def prompt(p, i=-1):
    return p.call_args_list[i].kwargs["json"]["contents"][0]["parts"][0]["text"]


def test_sans_secret():
    at, _ = lancer(secrets=False)
    assert "Configurez votre API KEY" in textes(at.error)[0]


def test_pari_conseille_avec_recherche():
    at, p = lancer([http()])
    assert not at.exception and not at.error, textes(at.error)
    assert p.call_count == 2
    recherche, analyse = p.call_args_list
    assert recherche.kwargs["json"]["tools"] == [{"google_search": {}}]
    assert "tools" not in analyse.kwargs["json"]
    assert analyse.kwargs["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert all(c.kwargs["headers"] == {"x-goog-api-key": "CLE-TEST"} for c in p.call_args_list)
    assert all("CLE-TEST" not in c.args[0] for c in p.call_args_list if c.args)
    assert "terrain : souple" in prompt(p).lower()  # contexte du jour transmis
    assert "Discipline : Obstacles" in prompt(p)  # détectée d'après la musique
    v = verdict(at)
    assert "✅ À JOUER" in v and "n° 4 FOREST DU PECOS" in v and "<b>5.8</b>" in v
    c = classement(at)
    assert c.index("LOKI DE LA BRUNIE") < c.index("FOREST DU PECOS")  # ordre de l'IA
    assert "PARI" in c and "🔥 OUTSIDER" in c
    assert any("Trio 5 - 4 - 1" in m and "non conseillé" in m for m in textes(at.markdown))


def test_pas_de_pari_sans_valeur():
    at, _ = lancer([http(json_=SANS_VALEUR)])
    v = verdict(at)
    assert "🚫 NE PAS JOUER" in v and "Aucun cheval n&#x27;est assez intéressant" in v


def test_pas_de_pari_sans_cotes():
    texte = "5 LOKI 1s 2s\n4 FOREST 1s 3s 5.8"
    reponse = {"chevaux": [{"num": "5", "p": 60}, {"num": "4", "p": 40}], "pari_nom": "Couplé", "pari_nums": "5 - 4"}
    at, _ = lancer([http(json_=reponse)], texte=texte, recherche=False)
    assert "Cote manquante (n° 5)" in verdict(at)


def test_profil_prudent_refuse_cote_trop_haute():
    at, _ = lancer([http()], profil="Prudent")
    assert "NE PAS JOUER" in verdict(at)


def test_sans_recherche_un_seul_appel():
    at, p = lancer([http()], recherche=False)
    assert p.call_count == 1 and "Aucune donnée du jour" in prompt(p)
    assert not at.error


def test_recherche_indisponible():
    at, p = lancer([http()], contexte=http(429))
    assert p.call_count == 2
    assert any("Recherche Google indisponible" in c for c in textes(at.caption))
    assert "À JOUER" in verdict(at)  # l'analyse a quand même eu lieu, sans données du jour
    assert "Aucune donnée du jour" in prompt(p)


def test_recherche_faite_une_fois_par_jour():
    at, p = lancer([http()])
    autre = SITE.replace("6.5", "6.6")  # autre course, même hippodrome
    with mock.patch("requests.post", side_effect=[http()]) as p2:
        at.text_area[0].input(autre)
        analyser(at).click().run()
    assert p2.call_count == 1 and "tools" not in p2.call_args.kwargs["json"]


def test_meme_course_en_cache():
    at, _ = lancer([http()])
    with mock.patch("requests.post", side_effect=[]) as p2:
        analyser(at).click().run()
    assert p2.call_count == 0 and "À JOUER" in verdict(at)


def test_discipline_contradictoire_signalee():
    at, p = lancer([http()], discipline="Trot", recherche=False)
    assert any("indique plutôt **Obstacles**" in c for c in textes(at.caption))
    assert "Discipline : Trot" in prompt(p)


def test_numero_inconnu_signale():
    reponse = {**AVEC_VALEUR, "chevaux": AVEC_VALEUR["chevaux"] + [{"num": "15", "p": 1}]}
    at, _ = lancer([http(json_=reponse)], recherche=False)
    assert any("n° 15, qui n'est pas au départ" in w for w in textes(at.warning))


@pytest.mark.parametrize("reponses, exc, message", [
    ([http(429)], None, "Quota Gemini dépassé"),
    (None, requests.Timeout(), "pas répondu à temps"),
    ([http(500)], None, "code 500"),
    ([http(texte="")], None, "vide ou bloquée"),
    ([http(texte="désolé, pas de JSON")], None, "Erreur d'analyse"),
    ([http(json_={"chevaux": [{"num": "99", "p": 50}]})], None, "Erreur d'analyse"),
])
def test_erreurs(reponses, exc, message):
    at, _ = lancer(reponses, exc=exc, recherche=False)
    assert not at.exception
    assert message in textes(at.error)[0]


def test_saisie_vide_et_lignes_ignorees():
    at, p = lancer([], texte="", recherche=False)
    assert "Veuillez saisir des partants" in textes(at.error)[0] and p.call_count == 0
    at, _ = lancer([http()], texte="Prix de Paris\n" + SITE, recherche=False)
    assert "Prix de Paris" in textes(at.warning)[0]


def test_historique_desactive_et_limite_non_verifiee():
    at, _ = lancer([http()], recherche=False)
    assert any("Historique désactivé" in i for i in textes(at.info))
    assert any("Limite de pertes non vérifiée" in c for c in textes(at.caption))
    assert not [b for b in at.button if "Enregistrer" in b.label]


def historique(*lignes):
    return pd.DataFrame([{"date": d, "hippodrome": "V", "discipline": "Obstacles", "profil": "Équilibré",
                          "pari": "Simple Gagnant", "chevaux": "1", "cote": 3.0, "proba_ia": .4,
                          "gain_espere": .2, "mise": m, "resultat": r, "gain_reel": g} for d, m, r, g in lignes])


def maintenant(delta_jours=0):
    return (pd.Timestamp.now() - pd.Timedelta(days=delta_jours)).strftime("%Y-%m-%d %H:%M")


def test_enregistrer_ticket():
    feuille = mock.Mock()
    feuille.read.side_effect = Exception("onglet absent")
    at, _ = lancer([http()], sheets=feuille, recherche=False)
    with mock.patch("streamlit.connection", return_value=feuille):
        [b for b in at.button if "Enregistrer le ticket" in b.label][0].click().run()
    assert feuille.create.call_count == 1
    ligne = feuille.create.call_args.kwargs["data"].iloc[0]
    assert ligne["pari"] == "Simple Gagnant" and ligne["chevaux"] == "4" and ligne["cote"] == 5.8
    assert 0 < ligne["mise"] <= 20 and ligne["resultat"] == "En attente"
    assert any("Ticket enregistré" in s for s in textes(at.success))


def test_limite_de_pertes_atteinte():
    feuille = mock.Mock()
    feuille.read.return_value = historique((maintenant(1), 60, "Perdu", 0), (maintenant(2), 50, "Perdu", 0))
    at, _ = lancer([http()], sheets=feuille, recherche=False)  # limite par défaut : 100 €
    assert "NE PAS JOUER" in verdict(at) and "Limite de pertes atteinte" in verdict(at)


def test_limite_de_pertes_reduit_la_mise():
    feuille = mock.Mock()
    feuille.read.return_value = historique((maintenant(1), 97, "Perdu", 0))
    at, _ = lancer([http()], sheets=feuille, recherche=False)
    assert "3,00\u00a0€" in verdict(at)


def test_stats_historique():
    feuille = mock.Mock()
    feuille.read.return_value = historique((maintenant(30), 20, "Gagné", 50), (maintenant(30), 20, "Perdu", 0))
    at, _ = lancer([], texte="", sheets=feuille, recherche=False)
    valeurs = {m.label: m.value for m in at.metric}
    assert valeurs["Bénéfice"] == "+10.00 €" and valeurs["ROI"] == "+25.0 %"
    assert valeurs["Perte 7 jours"] == "0.00 € / 100 €"


# --- Pronostics de la presse ------------------------------------------------

def test_presse_compilee_et_verifiee():
    at, p = lancer([http()], presse=PRESSE)
    assert not at.exception and not at.error
    assert p.call_count == 3  # contexte + presse (en parallèle) + analyse
    md = " ".join(textes(at.markdown))
    assert "Ce que disent les pronostiqueurs" in md
    assert "Sources (3)" in md and "Site inventé" not in md
    assert any("1 source(s) écartée(s) (Site inventé)" in c and "3 sites réellement consultés" in c
               for c in textes(at.caption))
    assert any("Geny cite des numéros absents (15)" in w for w in textes(at.warning))
    # consensus transmis à l'IA
    assert "PRONOSTICS PUBLIÉS" in prompt(p) and "n° 5 LOKI DE LA BRUNIE : 14 pts, cité par 3/3" in prompt(p)
    # verdict et classement indiquent l'avis de la presse
    assert "Pronostiqueurs : <b>cité par 3 sources sur 3 (1er choix de 1)</b>" in verdict(at)
    assert "📰 cité par 3 sources sur 3 (1er choix de 2)" in classement(at)


def test_presse_seulement_des_sources_inventees():
    inventee = http_presse([{"nom": "X", "site": "x-invente.fr", "selection": ["5"]}], consultees=("autre.fr",))
    at, p = lancer([http()], presse=inventee)
    assert any("Aucun pronostic vérifiable" in c for c in textes(at.caption))
    assert "PRONOSTICS PUBLIÉS" not in prompt(p)


def test_presse_indisponible():
    at, _ = lancer([http()], presse=http(429))
    assert any("Pronostics de la presse indisponibles" in c for c in textes(at.caption))
    assert "À JOUER" in verdict(at)


def test_presse_gardee_en_memoire():
    at, p = lancer([http()], presse=PRESSE)
    autre = SITE.replace("6.5", "6.4")  # même course, cote qui a bougé
    with mock.patch("requests.post", side_effect=gemini_simule([http()])) as p2:
        at.text_area[0].input(autre)
        analyser(at).click().run()
    assert p2.call_count == 1  # ni recherche du jour ni pronostics refaits



def test_presse_sans_page_consultee():
    sans_pages = http_presse([{"nom": "Paris-Turf", "site": "paris-turf.com", "selection": ["5"]}], consultees=())
    at, _ = lancer([http()], presse=sans_pages)
    assert any("aucune page vérifiable" in c and "(Paris-Turf)" in c for c in textes(at.caption))
