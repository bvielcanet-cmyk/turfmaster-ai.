"""Les feux du jour sur Telegram : quelles courses sont lisibles. Aucun pari, aucune mise.

Un message par passage. Il ne dépend pas de l'heure exacte, car les lancements planifiés de GitHub ne
sont pas fiables (1 passage constaté sur une centaine prévus les 21-22/11/2026). Rien n'est écrit dans
Google Sheets : cette tâche ne peut donc effacer aucune donnée.

Secrets GitHub facultatifs : TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID. Sans eux, le message est seulement affiché.
"""
import os
import sys
import time
from datetime import datetime
from html import escape

import requests

import decision
import pmu

MAX_COURSES = 10


def message(lignes, maintenant):
    entete = f"🚦 <b>Les feux du jour</b> (cotes de {maintenant:%H:%M}, elles bougeront)"
    avertissement = "🎲 Un feu dit si une course est lisible, pas si un pari est rentable. Aucun avantage démontré."
    if not lignes:
        return f"{entete}\nAucune course à afficher.\n{avertissement}"
    compte = " · ".join(f"{f['emoji']} {sum(x['feu'] == c for x in lignes)}" for c, f in decision.FEUX.items())
    corps = [f"{decision.FEUX[x['feu']]['emoji']} {x['heure']} {x['course']} {escape(x['hippodrome'])} : favori "
             f"{escape(x['favori'])}, {x['place']:.0%} d'être placé" for x in lignes[:MAX_COURSES]]
    return "\n".join([entete, compte, *corps, avertissement])


def main():
    maintenant = datetime.now(tz=pmu.PARIS)

    def lire_partants(*args):
        time.sleep(0.5)
        return pmu.partants(*args)

    try:
        lignes = decision.cribler(maintenant.date(), maintenant, pmu.programme(maintenant.date()), lire_partants)
    except pmu.PmuErreur as e:
        print(e)
        return 1
    texte = message(lignes, maintenant)
    print(texte)
    jeton, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (jeton and chat):
        return 0
    try:
        r = requests.post(f"https://api.telegram.org/bot{jeton}/sendMessage", timeout=15,
                          json={"chat_id": chat, "text": texte, "parse_mode": "HTML"})
    except requests.RequestException:
        print("Telegram injoignable")  # ne pas afficher l'exception : elle contient le jeton
        return 1
    if r.status_code != 200:
        print(f"Telegram : erreur {r.status_code}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
