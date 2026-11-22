"""Carnet des paris réellement joués : saisie libre, règlement aux rapports officiels, budget de la semaine."""
import pandas as pd

import decision
import mesure

EN_ATTENTE, GAGNE, PERDU, REMBOURSE = "En attente", "Gagné", "Perdu", "Remboursé"
RESULTATS = [EN_ATTENTE, GAGNE, PERDU, REMBOURSE]
# Mêmes premières colonnes que l'ancien onglet « TurfMaster » : les tickets existants restent lisibles
COLONNES = ["date", "hippodrome", "discipline", "profil", "pari", "chevaux", "cote", "proba_ia", "gain_espere",
            "mise", "resultat", "gain_reel", "course", "analyse", "source_gain", "date_course"]


def ligne(date, date_course, course, hippodrome, discipline, pari, num, cote, mise):
    return {**dict.fromkeys(COLONNES, ""), "date": date, "date_course": date_course, "course": course,
            "hippodrome": hippodrome, "discipline": discipline, "pari": pari, "chevaux": str(num),
            "cote": float(cote), "proba_ia": 0.0, "gain_espere": 0.0, "mise": float(mise),
            "resultat": EN_ATTENTE, "gain_reel": 0.0}


def regler(df, i, arrivee):
    """Règle le pari i avec l'arrivée PMU. True si réglé. Jamais de gain estimé : rapports officiels seulement."""
    t = df.loc[i]
    num, mise = mesure.texte_cellule(t["chevaux"]), float(t["mise"] or 0)
    if t["pari"] not in (decision.GAGNANT, decision.PLACE):
        return False
    if arrivee["annulee"] or num in arrivee["non_partants"]:
        resultat, rapporte = REMBOURSE, mise
        source = "course annulée" if arrivee["annulee"] else "non-partant"
    else:
        rapports = arrivee["rapports_gagnant" if t["pari"] == decision.GAGNANT else "rapports_place"]
        if not arrivee["terminee"] or not rapports:
            return False  # pas d'arrivée ou rapports pas encore publiés
        rapport = float(rapports.get(num, 0.0))
        resultat, rapporte = (GAGNE, round(mise * rapport, 2)) if rapport else (PERDU, 0.0)
        source = "rapport officiel PMU"
    df.at[i, "resultat"], df.at[i, "gain_reel"], df.at[i, "source_gain"] = resultat, rapporte, source
    return True


def bilan(df):
    """Bilan des paris réglés (remboursés exclus)."""
    t = df[df["resultat"].isin([GAGNE, PERDU])]
    mise = float(pd.to_numeric(t["mise"], errors="coerce").fillna(0).sum())
    rendu = float(pd.to_numeric(t["gain_reel"], errors="coerce").fillna(0).sum())
    return {"n": len(t), "attente": int((df["resultat"] == EN_ATTENTE).sum()),
            "gagnes": int((t["resultat"] == GAGNE).sum()), "mise": mise, "rendu": rendu, "net": rendu - mise}


def nombre_du_jour(df, jour):
    """Paris notés ce jour-là (remboursés exclus)."""
    if df.empty:
        return 0
    return int((df["date"].astype(str).str.startswith(jour.isoformat()) & (df["resultat"] != REMBOURSE)).sum())


def mise_semaine(df, maintenant, jours=7):
    """Total misé sur 7 jours, gagné ou perdu : un gain n'agrandit pas le budget."""
    if df.empty:
        return 0.0
    dates = pd.to_datetime(df["date"], errors="coerce", format="%Y-%m-%d %H:%M")
    t = df[(dates >= maintenant - pd.Timedelta(days=jours)) & (df["resultat"] != REMBOURSE)]
    return float(pd.to_numeric(t["mise"], errors="coerce").fillna(0).sum())
