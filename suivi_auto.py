"""Suivi automatique des conseils Placé, lancé toutes les 10 minutes par GitHub Actions.

À chaque passage :
  1. pour chaque course française qui part dans les 3 à 20 prochaines minutes, calcule le conseil
     Placé (règle « confirmée » et règle « corrigée », en essai), l'enregistre dans le Google Sheet
     (onglet ConseilsPlace) et envoie une alerte Telegram ;
  2. règle les conseils en attente dont la course est terminée (rapport officiel du Placé) et
     envoie un récapitulatif Telegram.

Configuration (variables d'environnement, à mettre dans les secrets du dépôt GitHub) :
  GSHEETS_CREDENTIALS : contenu du fichier JSON du compte de service Google
  GSHEETS_URL         : adresse du classeur Google Sheets
  TELEGRAM_BOT_TOKEN  : jeton du bot Telegram (facultatif)
  TELEGRAM_CHAT_ID    : identifiant de la conversation Telegram (facultatif)
  CAPITAL, PROFIL     : pour la mise affichée (par défaut 1000 et Équilibré)
  BUDGET, JOKER       : budget du plan du jour (50 € par défaut) et joker outsider (« oui » pour l'ajouter)

Entre 11 h 00 et 11 h 09, un résumé du « plan du jour » (3 meilleures courses, budget réparti selon
le profil) est aussi envoyé sur Telegram.

Sans GSHEETS_CREDENTIALS, le script tourne « à sec » : il affiche les conseils sans rien enregistrer.
"""
import json
import os
import sys
import time
from datetime import datetime

import pandas as pd
import requests

import mesure
import place
import plan
import pmu
import protection

FEUILLE = "ConseilsPlace"
AVANCE_MIN, AVANCE_MAX = 3, 20  # minutes avant le départ


# --- Google Sheets (hors Streamlit) --------------------------------------------------

def ouvrir_feuille():
    creds = os.environ.get("GSHEETS_CREDENTIALS")
    if not creds:
        return None
    import gspread
    client = gspread.service_account_from_dict(json.loads(creds))
    classeur = client.open_by_url(os.environ["GSHEETS_URL"])
    try:
        return classeur.worksheet(FEUILLE)
    except gspread.WorksheetNotFound:
        feuille = classeur.add_worksheet(FEUILLE, rows=1000, cols=len(place.COLONNES_SUIVI))
        feuille.append_row(place.COLONNES_SUIVI)
        return feuille


def lire(feuille):
    if feuille is None:
        return pd.DataFrame(columns=place.COLONNES_SUIVI)
    lignes = feuille.get_all_values()
    if not lignes:
        return pd.DataFrame(columns=place.COLONNES_SUIVI)
    df = pd.DataFrame(lignes[1:], columns=lignes[0]).replace("", None)
    for col in place.COLONNES_SUIVI:
        if col not in df.columns:
            df[col] = ""
    return mesure.normaliser(df[place.COLONNES_SUIVI])


def ecrire(feuille, df):
    if feuille is None:
        return
    valeurs = [place.COLONNES_SUIVI] + df[place.COLONNES_SUIVI].astype(object).where(df.notna(), "").values.tolist()
    feuille.clear()
    feuille.update(valeurs, "A1")


# --- Telegram -------------------------------------------------------------------------

def telegram(texte):
    jeton, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    print(texte, flush=True)
    if not (jeton and chat):
        return
    try:
        r = requests.post(f"https://api.telegram.org/bot{jeton}/sendMessage", timeout=15,
                          json={"chat_id": chat, "text": texte, "parse_mode": "HTML",
                                "disable_web_page_preview": True})
        if r.status_code != 200:
            print(f"Telegram : erreur {r.status_code}", flush=True)
    except requests.RequestException:
        print("Telegram injoignable", flush=True)


def message_conseil(c, course, conseil):
    essai = "" if conseil["regle"] == "confirmée" else "\n🧪 <i>Règle corrigée, en essai</i>"
    return (f"🎯 <b>Placé conseillé</b> — {course['id']} {course['hippodrome']} {course['heure']}\n"
            f"n° <b>{conseil['num']} {conseil['nom']}</b>\n"
            f"Cote Placé probable {conseil['cote_min']:g} – {conseil['cote_max']:g} "
            f"(jouer si le minimum reste ≥ {conseil['cote_mini_a_jouer']:.2f})\n"
            f"Chances de placé estimées ≈ {conseil['proba_corrigee']:.0%} · mise {c:.2f} €\n"
            f"Suivi à blanc : noté automatiquement.{essai}")


# --- Passage ----------------------------------------------------------------------------

def minutes_avant(course, maintenant):
    if course["heure"] == "?":
        return None
    h, m = map(int, course["heure"].split(":"))
    depart = maintenant.replace(hour=h, minute=m, second=0, microsecond=0)
    return (depart - maintenant).total_seconds() / 60


def relever_conseils(suivi, maintenant, capital, profil, pause=0.5):
    """Ajoute au suivi les conseils des courses qui partent bientôt. Retourne (suivi, messages)."""
    jour = maintenant.date()
    deja = set(zip(suivi["date_course"].astype(str), suivi["course"].astype(str),
                   suivi["regle"].astype(str).replace("", "confirmée")))
    messages = []
    for course in pmu.programme(jour):
        avance = minutes_avant(course, maintenant)
        if course["pays"] != "FRA" or course["statut"] != "à venir" or avance is None \
                or not (AVANCE_MIN <= avance <= AVANCE_MAX):
            continue
        time.sleep(pause)
        try:
            df = pmu.partants(jour, course["reunion"], course["course"])
            cotes = pmu.cotes_place(jour, course["reunion"], course["course"])
        except pmu.PmuErreur as e:
            print(course["id"], e, flush=True)
            continue
        for regle in place.REGLES:
            if (pmu.date_pmu(jour), course["id"], regle) in deja:
                continue
            conseil = place.conseil_place(df, cotes, profil, capital, regle=regle)
            if conseil is None:
                continue
            ligne = place.ligne_suivi("A" + maintenant.strftime("%Y%m%d%H%M%S") + course["id"] + regle[:3],
                                      maintenant.strftime("%Y-%m-%d %H:%M"), pmu.date_pmu(jour), course["id"],
                                      course["hippodrome"], conseil, source="automatique")
            suivi = place.ajouter_suivi(suivi, ligne)
            messages.append(message_conseil(conseil["mise"], course, conseil))
    return suivi, messages


def regler_attente(suivi):
    """Règle les conseils en attente. Retourne (suivi, lignes réglées)."""
    memo, regles = {}, []
    for i, c in suivi[suivi["resultat"] == "En attente"].iterrows():
        cle = (str(c["date_course"]).zfill(8), str(c["course"]))
        try:
            if cle not in memo:
                reunion, numero = pmu.decouper_id(cle[1])
                memo[cle] = pmu.arrivee(cle[0], reunion, numero)
            if place.regler(suivi, i, memo[cle]):
                regles.append(suivi.loc[i])
        except (pmu.PmuErreur, ValueError) as e:
            print(cle, e, flush=True)
    return suivi, regles


def message_bilan(regles, suivi):
    lignes = []
    for r in regles:
        icone = {"Placé": "✅", "Non placé": "❌"}.get(r["resultat"], "↩️")
        essai = " (essai)" if r["regle"] == "corrigée" else ""
        lignes.append(f"{icone} {r['course']} n° {r['num']} {r['nom']}{essai} : {r['resultat']}"
                      + (f" à {float(r['rapport']):.2f} €" if r["resultat"] == "Placé" else ""))
    bilan = place.stats_suivi(suivi, "confirmée")
    resume = (f"\n\n📊 Règle confirmée : {bilan['n']} conseils réglés, rendement "
              f"{bilan['rendement'] * 100:+.1f} %" if bilan["n"] else "")
    return "🏁 <b>Résultats</b>\n" + "\n".join(lignes) + resume


def plan_du_jour(maintenant, profil, facteur=1.0):
    budget = float(os.environ.get("BUDGET", 50)) * facteur
    conseils, vus = plan.cribler(maintenant.date(), maintenant, pause=0.3)
    selection, jok = plan.composer(conseils, budget, profil,
                                   os.environ.get("JOKER", "").lower() in ("oui", "1", "true"))
    return plan.texte_plan(selection, budget, profil, vus, jok)


def main():
    maintenant = datetime.now(tz=pmu.PARIS)
    capital = float(os.environ.get("CAPITAL", 1000))
    profil = os.environ.get("PROFIL", "Équilibré")
    feuille = ouvrir_feuille()
    if feuille is None:
        print("GSHEETS_CREDENTIALS absent : passage « à sec », rien n'est enregistré.", flush=True)
    suivi = lire(feuille)
    # Protection automatique : capital fictif du suivi à blanc, mises divisées par 2 après -15 %
    etat = protection.etat_courant(capital, None, suivi)
    if etat["reduit"]:
        print(f"Protection active : capital {etat['capital']:.2f} €, {etat['baisse']:.0%} sous le plus haut.", flush=True)
    suivi, messages = relever_conseils(suivi, maintenant, etat["capital"] * etat["facteur"], profil)
    suivi, regles = regler_attente(suivi)
    if maintenant.hour == 11 and maintenant.minute < 10:
        texte = plan_du_jour(maintenant, profil, etat["facteur"])
        if etat["reduit"]:
            texte += f"\n🛡️ Protection active : mises divisées par 2 (capital {etat['baisse']:.0%} sous son plus haut)."
        messages.insert(0, texte)
    if messages or regles:
        ecrire(feuille, suivi)
    for m in messages:
        telegram(m)
    if regles:
        telegram(message_bilan(regles, suivi))
    print(f"{maintenant:%H:%M} : {len(messages)} conseil(s), {len(regles)} réglé(s).", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
