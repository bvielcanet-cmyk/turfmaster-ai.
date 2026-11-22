"""Protection automatique des mises.

Stratégie retenue après comparaison sur 479 conseils Placé passés (22/09 -> 20/11/2026) :
  - la mise est un pourcentage du capital ACTUEL (recalculé à chaque fois) ;
  - dès que le capital est à plus de 15 % sous son plus haut, les mises sont divisées par deux,
    jusqu'à ce que le capital remonte au-dessus de ce seuil.
Résultat sur les conseils passés (cote Gagnant < 8, 1 % du capital) : même gain qu'avec une mise fixe
(capital 100 -> 184), mais risque de traverser une baisse de plus de 20 % ramené de 9 % à 3 %.

Le capital se calcule à partir des tickets réellement joués s'il y en a ; sinon, à partir du suivi
à blanc (capital fictif), pour que la protection soit déjà active pendant la phase de test.
"""
import pandas as pd

SEUIL_BAISSE = 0.15
FACTEUR_REDUIT = 0.5


def etat(capital_initial, gains_nets):
    """gains_nets : gains nets successifs, dans l'ordre chronologique.

    Retourne {"capital", "pic", "baisse", "reduit", "facteur"}."""
    capital = pic = float(capital_initial)
    for g in gains_nets:
        capital += float(g)
        pic = max(pic, capital)
    baisse = 1 - capital / pic if pic > 0 else 0.0
    reduit = baisse > SEUIL_BAISSE
    return {"capital": round(capital, 2), "pic": round(pic, 2), "baisse": baisse,
            "reduit": reduit, "facteur": FACTEUR_REDUIT if reduit else 1.0}


def gains_tickets(tickets):
    """Gains nets des tickets réellement joués et réglés (Gagné / Perdu), par date."""
    if tickets is None or tickets.empty:
        return []
    t = tickets[tickets["resultat"].isin(["Gagné", "Perdu"])].copy()
    t["_date"] = pd.to_datetime(t["date"], errors="coerce")
    t = t.sort_values("_date", kind="stable")
    gains = pd.to_numeric(t["gain_reel"], errors="coerce").fillna(0) - pd.to_numeric(t["mise"], errors="coerce").fillna(0)
    return gains.tolist()


def gains_suivi(suivi):
    """Gains nets fictifs des conseils Placé (règle confirmée) réglés, par date."""
    if suivi is None or suivi.empty:
        return []
    s = suivi[suivi["resultat"].isin(["Placé", "Non placé"])
              & (suivi["regle"].astype(str).replace("", "confirmée") == "confirmée")].copy()
    s["_date"] = pd.to_datetime(s["date"], errors="coerce")
    s = s.sort_values("_date", kind="stable")
    return pd.to_numeric(s["gain"], errors="coerce").fillna(0).tolist()


def etat_courant(capital_initial, tickets=None, suivi=None):
    """État calculé sur les tickets réels s'il y en a, sinon sur le suivi à blanc (fictif)."""
    reels = gains_tickets(tickets)
    if reels:
        return {**etat(capital_initial, reels), "source": "tickets joués"}
    return {**etat(capital_initial, gains_suivi(suivi)), "source": "suivi à blanc (fictif)"}
