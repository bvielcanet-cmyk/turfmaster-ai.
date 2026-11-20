"""Logique de TurfMaster, sans interface : lecture des partants, appel Gemini,
calcul de la mise et statistiques. Séparée de app.py pour pouvoir être testée."""
import json
import re

import pandas as pd
import requests

# --- Lecture des partants -------------------------------------------------

RE_FER = re.compile(r'^(D4|DP|DA)$', re.IGNORECASE)
RE_MUSIQUE = re.compile(r'\b\d{1,2}[admphsc]\b|\b[A-Z]D\b|\bD[admp]\b')
RE_COTE = re.compile(r'(?<![\w.,])(\d{1,3}[.,]\d{1,2})(?![\w.,])')


def _est_fin_du_nom(mot):
    """Un mot qui n'appartient plus au nom : ferrure, musique, cote, parenthèse..."""
    return bool(
        RE_FER.match(mot)
        or RE_MUSIQUE.fullmatch(mot)
        or re.match(r'^\d', mot)
        or mot.startswith('(')
        or not re.search(r'[A-Za-zÀ-ÿ]', mot)  # "---", "*", etc.
    )


def extraire_data_pro(texte):
    """Retourne (DataFrame des partants, liste des lignes non reconnues).

    Format attendu par ligne : NUMÉRO NOM [FERRURE] [MUSIQUE] [COTE]
    ex. « 12 FAKIR D4 1a 2a 4.5 »
    """
    data, ignorees = [], []
    for ligne in texte.strip().split('\n'):
        ligne = ligne.strip()
        if not ligne:
            continue
        num_match = re.match(r'^(\d{1,2})\s*[.\-):]?\s*', ligne)
        numero = num_match.group(1) if num_match else "?"
        reste = ligne[num_match.end():] if num_match else ligne

        mots = reste.split()
        nom_mots = []
        for mot in mots:
            if _est_fin_du_nom(mot):
                break
            nom_mots.append(mot)
        nom = " ".join(nom_mots).upper()
        if not re.search(r'[A-ZÀ-Ý]', nom):  # pas de lettre = pas un nom de cheval
            ignorees.append(ligne)
            continue

        suite = " ".join(mots[len(nom_mots):])
        fer = [m for m in re.findall(r'[A-Za-z0-9]+', suite) if RE_FER.match(m)]
        musique = RE_MUSIQUE.findall(suite)
        cotes = RE_COTE.findall(suite)
        cote = float(cotes[-1].replace(',', '.')) if cotes else None

        info = f"{fer[0].upper() if fer else 'F'} | {' '.join(musique) if musique else 'N/A'}"
        if cote is not None:
            info += f" | cote {cote:g}"
        data.append({"FULL_ID": f"{numero} - {nom}", "NUM": numero, "COTE": cote, "Info": info})
    return pd.DataFrame(data), ignorees


# --- Mise ----------------------------------------------------------------

POURCENTAGE_MISE = {"Prudent": 0.01, "Équilibré": 0.02, "Offensif": 0.04}

TYPES_PARI = {
    "Prudent": "un pari simple : Simple Placé ou Couplé Placé",
    "Équilibré": "un Couplé Gagnant, un Trio ou un Couplé Placé",
    "Offensif": "un Trio Ordre, un Quarté+ ou un Quinté+ (si la course le permet)",
}


def calculer_mise(capital, profil):
    """Mise fixe en pourcentage du capital selon le profil (1 %, 2 % ou 4 %)."""
    return round(max(float(capital), 0) * POURCENTAGE_MISE[profil], 2)


# --- Gemini --------------------------------------------------------------

class GeminiErreur(Exception):
    """Erreur affichable telle quelle (ne contient jamais la clé API)."""


def construire_prompt(partants_str, hippo, discipline, profil, recherche):
    if recherche:
        consigne_infos = (f"Utilise la recherche Google pour trouver la course du jour à {hippo} "
                          "(météo, distance, état du terrain, cotes actuelles si disponibles).")
    else:
        consigne_infos = ("Tu n'as pas accès à internet : si tu ne connais pas la météo ou la distance, "
                          "mets \"❔\" plutôt que d'inventer.")
    return f"""Expert Turf. Hippodrome : {hippo} | Discipline : {discipline} | Profil du parieur : {profil}.

PARTANTS (numéros réels, ferrure | musique | cote éventuelle) :
{partants_str}

MISSION :
1. {consigne_infos}
2. Classe les 5 chevaux les plus probables avec leur probabilité estimée.
3. Indique avec "out": true le cheval que tu considères comme outsider (au plus un), false pour les autres.
4. Propose {TYPES_PARI[profil]}, avec UNIQUEMENT les numéros des chevaux.
5. "gain" = gain net estimé pour une mise de 1 €, si tu peux l'estimer à partir des cotes, sinon "?".

RÉPONDS UNIQUEMENT AVEC CE JSON :
{{
    "m": "☀️", "d": "2700m", "r": "Faible | Modéré | Élevé", "ordre": "Num - Num - Num",
    "podium": [
        {{"n": "NUM - NOM", "p": "38%", "out": false}},
        {{"n": "NUM - NOM", "p": "22%", "out": false}},
        {{"n": "NUM - NOM", "p": "15%", "out": false}},
        {{"n": "NUM - NOM", "p": "11%", "out": true}},
        {{"n": "NUM - NOM", "p": "8%", "out": false}}
    ],
    "pari_nom": "Trio",
    "pari_nums": "12 - 4 - 7",
    "gain": "+2.50€"
}}
"""


URL_V1 = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"
URL_V1BETA = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

MESSAGES_HTTP = {
    400: "Requête refusée par Gemini (clé API invalide ?).",
    403: "Accès refusé : vérifiez la clé API et ses droits.",
    429: "Quota Gemini dépassé. Patientez un peu avant de réessayer.",
}


def _poster(url, api_key, payload):
    # La clé passe dans un en-tête et non dans l'URL : elle n'apparaît pas dans les journaux.
    try:
        return requests.post(url, json=payload, headers={"x-goog-api-key": api_key}, timeout=40)
    except requests.Timeout:
        raise GeminiErreur("Gemini n'a pas répondu à temps. Réessayez.")
    except requests.RequestException:
        raise GeminiErreur("Impossible de joindre Gemini (problème réseau).")


def _texte_reponse(response):
    try:
        parts = response.json()['candidates'][0]['content']['parts']
        texte = "".join(p.get('text', '') for p in parts)
    except (ValueError, KeyError, IndexError, TypeError):
        texte = ""
    if not texte.strip():
        raise GeminiErreur("Réponse de Gemini vide ou bloquée. Réessayez.")
    return texte


def appeler_gemini(api_key, prompt, recherche):
    """Retourne (texte, recherche_utilisee). Lève GeminiErreur en cas d'échec.

    Avec la recherche Google, si Gemini refuse l'option (non disponible, quota de
    recherche épuisé), on refait automatiquement la demande sans recherche.
    """
    base = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
    if recherche:
        response = _poster(URL_V1BETA, api_key, {**base, "tools": [{"google_search": {}}]})
        if response.status_code == 200:
            return _texte_reponse(response), True
        if response.status_code not in (400, 403, 429):
            raise GeminiErreur(f"Gemini a renvoyé une erreur (code {response.status_code}).")
    response = _poster(URL_V1, api_key, base)
    if response.status_code != 200:
        raise GeminiErreur(MESSAGES_HTTP.get(
            response.status_code, f"Gemini a renvoyé une erreur (code {response.status_code})."))
    return _texte_reponse(response), False


def extraire_json(texte):
    """Récupère l'objet JSON même si Gemini ajoute du texte ou des ``` autour."""
    debut, fin = texte.find('{'), texte.rfind('}')
    if debut == -1 or fin == -1:
        raise ValueError("Aucun JSON dans la réponse")
    return json.loads(texte[debut:fin + 1])


def valider_reponse(res):
    """Vérifie et normalise la réponse de Gemini. Lève ValueError si inutilisable."""
    if not isinstance(res, dict) or not isinstance(res.get('podium'), list) or not res['podium']:
        raise ValueError("Podium absent")
    podium = []
    for p in res['podium'][:5]:
        if not isinstance(p, dict) or 'n' not in p:
            raise ValueError("Cheval mal formé")
        podium.append({"n": str(p['n']), "p": str(p.get('p', '?')), "out": p.get('out') is True})
    # Au plus un outsider : on garde le premier signalé
    vu = False
    for p in podium:
        p['out'], vu = (p['out'] and not vu), (vu or p['out'])
    for cle in ('pari_nom', 'pari_nums'):
        if not res.get(cle):
            raise ValueError(f"Champ {cle} manquant")
    return {
        "m": str(res.get('m', '❔')), "d": str(res.get('d', '❔')), "r": str(res.get('r', '?')),
        "ordre": str(res.get('ordre', ' - '.join(p['n'].split(' - ')[0] for p in podium[:3]))),
        "podium": podium,
        "pari_nom": str(res['pari_nom']), "pari_nums": str(res['pari_nums']),
        "gain": str(res.get('gain', '?')),
    }


# --- Historique ----------------------------------------------------------

COLONNES_HISTORIQUE = ["date", "hippodrome", "discipline", "profil", "pari", "chevaux",
                       "mise", "resultat", "gain_reel"]
RESULTATS = ["En attente", "Gagné", "Perdu"]


def ligne_historique(date, hippo, discipline, profil, res, mise):
    return {"date": date, "hippodrome": hippo, "discipline": discipline, "profil": profil,
            "pari": res['pari_nom'], "chevaux": res['pari_nums'], "mise": mise,
            "resultat": "En attente", "gain_reel": 0.0}


def calculer_stats(df):
    """Statistiques sur les tickets dont le résultat est connu (Gagné / Perdu).

    gain_reel = somme rapportée par le ticket (0 si perdu).
    """
    if df is None or df.empty:
        resolus = pd.DataFrame(columns=COLONNES_HISTORIQUE)
    else:
        resolus = df[df['resultat'].isin(["Gagné", "Perdu"])]
    mises = pd.to_numeric(resolus['mise'], errors='coerce').fillna(0)
    gains = pd.to_numeric(resolus['gain_reel'], errors='coerce').fillna(0)
    total_mise, total_gain = float(mises.sum()), float(gains.sum())
    nb = len(resolus)
    return {
        "nb_tickets": 0 if df is None else len(df),
        "nb_resolus": nb,
        "reussite": (resolus['resultat'] == "Gagné").sum() / nb * 100 if nb else 0.0,
        "mise_totale": total_mise,
        "gains_totaux": total_gain,
        "benefice": total_gain - total_mise,
        "roi": (total_gain - total_mise) / total_mise * 100 if total_mise else 0.0,
    }
