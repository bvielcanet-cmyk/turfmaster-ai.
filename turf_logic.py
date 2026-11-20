"""Logique de TurfMaster, sans interface : lecture des partants, appel Gemini,
calcul de la mise et statistiques. Séparée de app.py pour pouvoir être testée."""
import json
import re
import unicodedata

import pandas as pd
import requests

# --- Lecture des partants -------------------------------------------------

RE_FER = re.compile(r'^(D4|DP|DA)$', re.IGNORECASE)
# Musique : place + discipline (1a, 10p, 2s...), ou lettre + discipline
# (T = tombé, A = arrêté, D = disqualifié, R = rétrogradé : Ts, As, Da...)
RE_MUSIQUE = re.compile(r'\b\d{1,2}[admphsc]\b|\b[TADR][admphsc]\b')
RE_MUSIQUE_ANNEES = re.compile(r'\(\d{2}\)|\b\d{1,2}[admphsc]\b|\b[TADR][admphsc]\b')
RE_COTE = re.compile(r'(?<![\w.,])(\d{1,3}[.,]\d{1,2})(?![\w.,])')
RE_POIDS = re.compile(r'(?<![\w.,])(\d{2}(?:[.,]\d)?)\s?kg\b', re.IGNORECASE)
RE_SEXE_AGE = re.compile(r'\b([HFM])/(\d{1,2})\b')
RE_NUMERO_SEUL = re.compile(r'^\d{1,2}$')
RE_JOCKEY = re.compile(r'^[^\d|]+\s-\s[^\d|]+$')  # « Zuliani L. - Lagarde F. »


def _est_fin_du_nom(mot):
    """Un mot qui n'appartient plus au nom : ferrure, musique, cote, parenthèse..."""
    return bool(
        RE_FER.match(mot)
        or RE_MUSIQUE.fullmatch(mot)
        or re.match(r'^\d', mot)
        or mot.startswith('(')
        or not re.search(r'[A-Za-zÀ-ÿ]', mot)  # "---", "*", etc.
    )


def _separer_nom(texte):
    """Coupe « FAKIR D4 1a » en ("FAKIR", "D4 1a")."""
    mots = texte.split()
    nom_mots = []
    for mot in mots:
        if _est_fin_du_nom(mot):
            break
        nom_mots.append(mot)
    return " ".join(nom_mots).upper(), " ".join(mots[len(nom_mots):])


def _fiche(numero, nom, suite, jockey=None, annees=False):
    """Construit la ligne du partant à partir du texte qui suit son nom."""
    fer = [m for m in re.findall(r'[A-Za-z0-9]+', suite) if RE_FER.match(m)]
    poids = RE_POIDS.search(suite)
    sans_poids = RE_POIDS.sub(" ", suite)  # un poids « 64,5 kg » n'est pas une cote
    musique = (RE_MUSIQUE_ANNEES if annees else RE_MUSIQUE).findall(sans_poids)
    cotes = RE_COTE.findall(sans_poids)
    cote = float(cotes[-1].replace(',', '.')) if cotes else None
    sexe_age = RE_SEXE_AGE.search(suite)

    morceaux = [fer[0].upper() if fer else 'F', ' '.join(musique) if musique else 'N/A']
    if sexe_age:
        morceaux.append(sexe_age.group(0))
    if poids:
        morceaux.append(f"{poids.group(1)} kg")
    if jockey:
        morceaux.append(jockey.replace(" - ", " / "))
    if cote is not None:
        morceaux.append(f"cote {cote:g}")
    return {"FULL_ID": f"{numero} - {nom}", "NUM": numero, "NOM": nom, "COTE": cote,
            "MUSIQUE": " ".join(musique), "Info": " | ".join(morceaux)}


def _lire_fiches(lignes):
    """Format copié depuis un site de courses : une fiche de plusieurs lignes par cheval.

        1
        ISISDELAGARDE
        Zuliani L. - Lagarde F.
        H/8   69 kg   2s 5s 1s (25) 3s ...   6.5
    """
    data, ignorees, fiche = [], [], None
    for ligne in lignes + [None]:
        if ligne is None or RE_NUMERO_SEUL.match(ligne):
            if fiche is not None:
                nom_ligne, *autres = fiche["lignes"] or [""]
                nom, suite = _separer_nom(nom_ligne)
                if re.search(r'[A-ZÀ-Ý]', nom):
                    i_jockey = next((i for i, l in enumerate(autres) if RE_JOCKEY.match(l)), None)
                    jockey = autres[i_jockey] if i_jockey is not None else None
                    suite = " ".join([suite] + [l for i, l in enumerate(autres) if i != i_jockey])
                    data.append(_fiche(fiche["numero"], nom, suite, jockey, annees=True))
                else:
                    ignorees.append(f"N° {fiche['numero']} (nom introuvable)")
            fiche = {"numero": ligne, "lignes": []} if ligne else None
        elif fiche is None:
            ignorees.append(ligne)  # texte avant le premier numéro
        else:
            fiche["lignes"].append(ligne)
    return data, ignorees


def extraire_data_pro(texte):
    """Retourne (DataFrame des partants, liste des lignes non reconnues).

    Deux formats acceptés :
    - une ligne par cheval : NUMÉRO NOM [FERRURE] [MUSIQUE] [COTE], ex. « 12 FAKIR D4 1a 2a 4.5 » ;
    - le copier-coller d'un site : numéro seul sur sa ligne, puis nom, jockey - entraîneur,
      sexe/âge, poids, musique et cote sur les lignes suivantes.
    """
    lignes = [l.strip() for l in texte.strip().split('\n') if l.strip()]
    if any(RE_NUMERO_SEUL.match(l) for l in lignes):
        data, ignorees = _lire_fiches(lignes)
        return pd.DataFrame(data), ignorees

    data, ignorees = [], []
    for ligne in lignes:
        num_match = re.match(r'^(\d{1,2})\s*[.\-):]?\s*', ligne)
        numero = num_match.group(1) if num_match else "?"
        reste = ligne[num_match.end():] if num_match else ligne
        nom, suite = _separer_nom(reste)
        if not re.search(r'[A-ZÀ-Ý]', nom):  # pas de lettre = pas un nom de cheval
            ignorees.append(ligne)
            continue
        data.append(_fiche(numero, nom, suite))
    return pd.DataFrame(data), ignorees



# --- Discipline ----------------------------------------------------------

LETTRES_DISCIPLINE = {"a": "Trot", "m": "Trot", "p": "Plat", "h": "Obstacles", "s": "Obstacles", "c": "Obstacles"}
DISCIPLINES = ["Trot", "Plat", "Obstacles"]


def detecter_discipline(df):
    """Discipline la plus fréquente dans les musiques (a/m = trot, p = plat, h/s/c = obstacles), ou None."""
    compte = {}
    if df.empty or "MUSIQUE" not in df:
        return None
    for musique in df["MUSIQUE"]:
        for lettre in re.findall(r'(?:\d|[TADR])([admphsc])\b', musique or ""):
            d = LETTRES_DISCIPLINE[lettre]
            compte[d] = compte.get(d, 0) + 1
    return max(compte, key=compte.get) if compte else None


# --- Valeur du pari et décision ------------------------------------------
#
# Un pari n'est conseillé que si son intérêt est MESURABLE : il faut la cote de
# chaque partant.
#   1. Probabilité retenue = moyenne entre l'estimation de l'IA et celle du marché
#      (les cotes). L'IA peut se tromper, surtout sur les petites probabilités :
#      on ne lui fait confiance qu'à moitié (CONFIANCE_IA).
#   2. Gain espéré pour 1 € misé en Simple Gagnant = probabilité retenue × cote − 1.
#   3. Pari conseillé seulement si le gain espéré, la probabilité et la cote
#      respectent les seuils du profil.
#   4. Mise = fraction du critère de Kelly, plafonnée en % du capital.

CONFIANCE_IA = 0.5

PROFILS = {
    "Prudent":   {"ev_min": 0.10, "p_min": 0.30, "cote_max": 4,  "kelly": 0.25, "plafond": 0.01},
    "Équilibré": {"ev_min": 0.08, "p_min": 0.15, "cote_max": 10, "kelly": 0.25, "plafond": 0.02},
    "Offensif":  {"ev_min": 0.05, "p_min": 0.08, "cote_max": 25, "kelly": 0.50, "plafond": 0.04},
}


def decrire_profil(profil):
    r = PROFILS[profil]
    return (f"gain espéré ≥ {r['ev_min']:+.0%}, probabilité ≥ {r['p_min']:.0%}, "
            f"cote ≤ {r['cote_max']}, mise ≤ {r['plafond']:.0%} du capital")

TYPES_PARI = {
    "Prudent": "un Simple Placé ou un Couplé Placé",
    "Équilibré": "un Couplé Gagnant, un Trio ou un Couplé Placé",
    "Offensif": "un Trio Ordre, un Quarté+ ou un Quinté+ (si la course le permet)",
}


def probas_marche(df):
    """Probabilités de victoire selon les cotes, marge des opérateurs retirée.
    Retourne None si une cote manque (le marché n'est alors pas mesurable)."""
    if df.empty or df["COTE"].isna().any():
        return None
    inverses = {row["NUM"]: 1 / row["COTE"] for _, row in df.iterrows() if row["COTE"] > 0}
    if len(inverses) != len(df):
        return None
    total = sum(inverses.values())
    return {num: inv / total for num, inv in inverses.items()}


def evaluer_pari(chevaux, df, capital, profil, budget_restant=None):
    """Décide s'il faut jouer.

    chevaux : sortie de valider_reponse()['chevaux'] (num, p entre 0 et 1).
    budget_restant : pertes encore autorisées sur la période (None = pas de limite).
    Retourne {"jouer", "raison" (phrase courte), "detail", "pari", "analyse"}.
    """
    regles = PROFILS[profil]
    marche = probas_marche(df)
    ia = {c["num"]: c["p"] for c in chevaux}
    lignes = []
    for _, row in df.iterrows():
        num, cote = row["NUM"], row["COTE"]
        p = ia.get(num)
        cote = None if pd.isna(cote) else float(cote)
        q = marche.get(num) if marche else None
        retenue = CONFIANCE_IA * p + (1 - CONFIANCE_IA) * q if (p is not None and q is not None) else None
        lignes.append({
            "num": num, "nom": row["NOM"], "cote": cote, "proba_ia": p, "proba_marche": q,
            "proba_retenue": retenue,
            "gain_espere": retenue * cote - 1 if retenue is not None else None,
        })
    analyse = pd.DataFrame(lignes).sort_values("proba_ia", ascending=False, na_position="last")
    resultat = {"jouer": False, "pari": None, "analyse": analyse, "raison": None, "detail": None}

    if marche is None:
        manquantes = [str(n) for n in df.loc[df["COTE"].isna(), "NUM"]]
        resultat["raison"] = f"Cote manquante (n° {', '.join(manquantes)})."
        resultat["detail"] = ("Sans la cote de chaque partant, le gain ne peut pas être mesuré. "
                              "Collez les partants avec leurs cotes.")
        return resultat

    # Chevaux compatibles avec le profil (probabilité et cote), puis seuil de gain espéré
    compatibles = [l for l in lignes if l["gain_espere"] is not None
                   and l["proba_retenue"] >= regles["p_min"] and l["cote"] <= regles["cote_max"]]
    candidats = [l for l in compatibles if l["gain_espere"] >= regles["ev_min"]]
    if not candidats:
        meilleur = max(compatibles, key=lambda l: l["gain_espere"], default=None)
        resultat["raison"] = f"Aucun cheval n'est assez intéressant pour le profil {profil}."
        resultat["detail"] = (
            f"Le meilleur, n° {meilleur['num']} {meilleur['nom']}, n'offre que "
            f"{meilleur['gain_espere']:+.0%} de gain espéré : il faut au moins {regles['ev_min']:+.0%}."
            if meilleur else
            f"Aucun cheval n'a à la fois une probabilité ≥ {regles['p_min']:.0%} "
            f"et une cote ≤ {regles['cote_max']}.")
        return resultat

    choix = max(candidats, key=lambda l: l["gain_espere"])
    kelly = (choix["proba_retenue"] * choix["cote"] - 1) / (choix["cote"] - 1)
    fraction = min(regles["kelly"] * kelly, regles["plafond"])
    mise = round(max(float(capital), 0) * fraction, 2)
    if budget_restant is not None:
        if budget_restant <= 0:
            resultat["raison"] = "Limite de pertes atteinte sur 7 jours."
            resultat["detail"] = "Aucun nouveau pari tant que les pertes de la semaine n'ont pas baissé."
            return resultat
        mise = round(min(mise, budget_restant), 2)
    if mise <= 0:
        resultat["raison"] = "Capital nul : pas de mise possible."
        resultat["detail"] = "Indiquez votre capital dans la barre latérale."
        return resultat

    resultat.update(jouer=True, raison=None, pari={**choix, "type": "Simple Gagnant", "mise": mise,
                                                  "fraction": mise / capital if capital else 0})
    return resultat


def pertes_recentes(historique, maintenant, jours=7):
    """Perte nette (mises − sommes rapportées) des tickets des `jours` derniers jours.
    Les tickets en attente comptent leur mise : c'est de l'argent engagé."""
    if historique is None or historique.empty:
        return 0.0
    dates = pd.to_datetime(historique["date"], errors="coerce", format="%Y-%m-%d %H:%M")
    recents = historique[dates >= maintenant - pd.Timedelta(days=jours)]
    mises = pd.to_numeric(recents["mise"], errors="coerce").fillna(0).sum()
    gains = pd.to_numeric(recents["gain_reel"], errors="coerce").fillna(0).sum()
    return float(mises - gains)


# --- Gemini --------------------------------------------------------------

class GeminiErreur(Exception):
    """Erreur affichable telle quelle (ne contient jamais la clé API)."""


URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

MESSAGES_HTTP = {
    400: "Requête refusée par Gemini (clé API invalide ?).",
    403: "Accès refusé : vérifiez la clé API et ses droits.",
    429: "Quota Gemini dépassé. Patientez un peu avant de réessayer.",
}


def _requete(api_key, payload):
    """Appel brut à Gemini, retourne la réponse JSON. Lève GeminiErreur."""
    # La clé passe dans un en-tête et non dans l'URL : elle n'apparaît pas dans les journaux.
    try:
        response = requests.post(URL_GEMINI, json=payload, headers={"x-goog-api-key": api_key}, timeout=60)
    except requests.Timeout:
        raise GeminiErreur("Gemini n'a pas répondu à temps. Réessayez.")
    except requests.RequestException:
        raise GeminiErreur("Impossible de joindre Gemini (problème réseau).")
    if response.status_code != 200:
        raise GeminiErreur(MESSAGES_HTTP.get(
            response.status_code, f"Gemini a renvoyé une erreur (code {response.status_code})."))
    try:
        return response.json()
    except ValueError:
        raise GeminiErreur("Réponse de Gemini illisible. Réessayez.")


def _texte(data):
    try:
        parts = data['candidates'][0]['content']['parts']
        texte = "".join(p.get('text', '') for p in parts)
    except (KeyError, IndexError, TypeError, AttributeError):
        texte = ""
    if not texte.strip():
        raise GeminiErreur("Réponse de Gemini vide ou bloquée. Réessayez.")
    return texte


def _poster(api_key, payload):
    return _texte(_requete(api_key, payload))


def rechercher_contexte(api_key, hippo, discipline, jour):
    """Recherche Google des infos du jour (météo, terrain, distances). Lève GeminiErreur."""
    prompt = (f"Nous sommes le {jour}. Recherche la réunion de courses hippiques à {hippo} aujourd'hui "
              f"(discipline : {discipline}). Réponds en texte court : météo, état du terrain, puis la liste "
              "des courses (nom, heure, distance, principaux partants). Si tu ne trouves rien de fiable, "
              "écris seulement : AUCUNE DONNÉE.")
    return _poster(api_key, {"contents": [{"parts": [{"text": prompt}]}],
                             "tools": [{"google_search": {}}],
                             "generationConfig": {"temperature": 0.1}})


def construire_prompt(partants_str, hippo, discipline, profil, contexte, presse=None):
    if contexte and "AUCUNE DONNÉE" not in contexte:
        bloc_contexte = f"CONTEXTE DU JOUR (recherche internet) :\n{contexte}"
    else:
        bloc_contexte = ("Aucune donnée du jour : si tu ne connais pas la météo ou la distance, "
                         "mets \"❔\" plutôt que d'inventer.")
    if presse:
        bloc_contexte += ("\n\nPRONOSTICS PUBLIÉS (compilés depuis la presse et les sites de pronostics) :\n"
                          f"{presse}\nC'est un avis parmi d'autres : les pronostiqueurs influencent aussi "
                          "les cotes. Garde ton propre jugement.")
    return f"""Expert Turf. Hippodrome : {hippo} | Discipline : {discipline}.

PARTANTS (numéro réel - nom (ferrure | musique, "(25)" = année 2025 | puis si connus :
sexe/âge | poids | jockey / entraîneur | cote)) :
{partants_str}

{bloc_contexte}

MISSION :
1. Estime pour CHAQUE partant sa probabilité de GAGNER, en %, la somme faisant 100.
   Fais ta propre analyse (forme, musique, poids, jockey, terrain, distance) : les cotes
   donnent l'avis des parieurs, ne te contente pas de les recopier.
2. Mets "out": true pour au plus un outsider (cheval peu coté qui a selon toi une vraie chance).
3. Propose une idée de pari combiné adaptée au profil {profil} : {TYPES_PARI[profil]},
   avec UNIQUEMENT des numéros de la liste.

Réponds avec un JSON de cette forme. Les valeurs entre <> sont à remplacer par TES
estimations pour CETTE course : ne recopie aucun exemple.
{{
    "m": "<emoji météo, ou ❔>", "d": "<distance réelle, ou ❔>", "r": "<Faible, Modéré ou Élevé>",
    "chevaux": [
        {{"num": "<NUM>", "p": <probabilité de victoire en %>, "out": <true ou false>}},
        ... un objet par partant
    ],
    "pari_nom": "<type de pari combiné>",
    "pari_nums": "<NUM> - <NUM> - ..."
}}
"""


def analyser(api_key, prompt):
    """Analyse sans recherche, réponse JSON imposée. Lève GeminiErreur."""
    return _poster(api_key, {"contents": [{"parts": [{"text": prompt}]}],
                             "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}})


def extraire_json(texte):
    """Récupère l'objet JSON même si Gemini ajoute du texte ou des ``` autour."""
    debut, fin = texte.find('{'), texte.rfind('}')
    if debut == -1 or fin == -1:
        raise ValueError("Aucun JSON dans la réponse")
    return json.loads(texte[debut:fin + 1])


def _numero(valeur):
    m = re.match(r'\s*(\d{1,2})', str(valeur))
    return str(int(m.group(1))) if m else None


def _proba(valeur):
    m = re.search(r'\d+(?:[.,]\d+)?', str(valeur))
    return float(m.group(0).replace(',', '.')) if m else None


def valider_reponse(res, df):
    """Vérifie la réponse de Gemini par rapport aux partants.

    Retourne (réponse normalisée, alertes). Les numéros inconnus sont écartés et signalés.
    Lève ValueError si la réponse est inutilisable.
    """
    if not isinstance(res, dict) or not isinstance(res.get("chevaux"), list):
        raise ValueError("Liste des chevaux absente")
    noms = {str(int(n)): nom for n, nom in zip(df["NUM"], df["NOM"]) if str(n).isdigit()}
    alertes, chevaux, vus = [], [], set()
    for c in res["chevaux"]:
        if not isinstance(c, dict):
            continue
        num, p = _numero(c.get("num")), _proba(c.get("p"))
        if num is None or p is None:
            continue
        if num not in noms:
            alertes.append(f"Gemini a cité le n° {num}, qui n'est pas au départ : ignoré.")
            continue
        if num in vus:
            continue
        vus.add(num)
        chevaux.append({"num": num, "nom": noms[num], "p": p, "out": c.get("out") is True})
    if not chevaux:
        raise ValueError("Aucun cheval valide")

    total = sum(c["p"] for c in chevaux)
    if total > 1.5:  # pourcentages -> fractions
        for c in chevaux:
            c["p"] /= 100
        total /= 100
    if total > 1:  # la somme ne peut pas dépasser 100 %
        for c in chevaux:
            c["p"] /= total
    chevaux.sort(key=lambda c: c["p"], reverse=True)
    vu_out = False
    for c in chevaux:
        c["out"], vu_out = (c["out"] and not vu_out), (vu_out or c["out"])

    combine = None
    nums_pari = re.findall(r'\d{1,2}', str(res.get("pari_nums", "")))
    if res.get("pari_nom") and nums_pari:
        inconnus = [n for n in nums_pari if str(int(n)) not in noms]
        if inconnus:
            alertes.append(f"Le combiné proposé contient des numéros absents ({', '.join(inconnus)}) : écarté.")
        else:
            combine = {"nom": str(res["pari_nom"]), "nums": " - ".join(str(int(n)) for n in nums_pari)}

    return {"m": str(res.get("m", "❔")), "d": str(res.get("d", "❔")), "r": str(res.get("r", "?")),
            "chevaux": chevaux, "combine": combine}, alertes


# --- Pronostics publiés -----------------------------------------------------
#
# Gemini cherche les pronostics publiés pour la course. Pour éviter les sources
# inventées, on ne garde que celles dont le site figure dans les pages que la
# recherche Google a réellement consultées (« groundingChunks »).

POINTS_RANG = [5, 4, 3, 2, 1]  # 1er choix d'une source = 5 points ... 5e choix = 1 point


def _canon(texte):
    """« Fréquence-Turf » -> « frequenceturf » : minuscules, sans accents ni ponctuation."""
    sans_accents = unicodedata.normalize("NFKD", str(texte or "")).encode("ascii", "ignore").decode()
    return re.sub(r'[^a-z0-9]', '', sans_accents.lower())


def _source_consultee(site, nom, domaines):
    """Domaine consulté qui correspond à la source, ou None.

    Gemini écrit parfois le domaine autrement (« frequenceturf.fr » pour « frequence-turf.fr ») :
    on compare sans tirets ni accents, sur le domaine puis sur le nom de la source."""
    dom = _domaine(site)
    for d in domaines:
        base = _canon(d.rsplit(".", 1)[0])
        if dom and (_canon(dom) == _canon(d) or _canon(dom.rsplit(".", 1)[0]) == base
                    or dom.endswith("." + d) or d.endswith("." + dom)):
            return d
        if len(base) >= 5 and _canon(nom) == base:
            return d
    return None


def _domaine(texte):
    m = re.search(r'((?:[a-z0-9-]+\.)+[a-z]{2,})', str(texte or "").lower())
    return m.group(1).removeprefix("www.") if m else None


def rechercher_pronostics(api_key, hippo, discipline, jour, partants_str):
    """Retourne (texte de la réponse, sources consultées [{"titre", "url", "domaine"}]). Lève GeminiErreur."""
    prompt = f"""Nous sommes le {jour}. Cherche sur internet les PRONOSTICS publiés pour cette course
({discipline}, {hippo}, aujourd'hui) : presse hippique, sites de pronostics, journaux.

Partants (numéro - nom) :
{partants_str}

Pour chaque source trouvée, donne sa sélection (numéros des chevaux, dans l'ordre de préférence,
5 au maximum). N'invente rien : ne cite que des sources que tu as réellement trouvées pendant
ta recherche, avec leur site. Si tu ne trouves aucun pronostic pour cette course, renvoie "sources": [].

Réponds UNIQUEMENT avec ce JSON :
{{"sources": [{{"nom": "<nom de la source>", "site": "<domaine, ex. exemple.fr>", "selection": ["<NUM>", "<NUM>"]}}]}}
"""
    data = _requete(api_key, {"contents": [{"parts": [{"text": prompt}]}],
                              "tools": [{"google_search": {}}],
                              "generationConfig": {"temperature": 0.1}})
    texte = _texte(data)
    consultees = []
    try:
        chunks = data['candidates'][0].get('groundingMetadata', {}).get('groundingChunks', [])
    except (KeyError, IndexError, AttributeError):
        chunks = []
    for ch in chunks:
        web = ch.get("web", {}) if isinstance(ch, dict) else {}
        dom = _domaine(web.get("title")) or _domaine(web.get("uri"))
        if dom:
            consultees.append({"titre": web.get("title", dom), "url": web.get("uri"), "domaine": dom})
    return texte, consultees


def compiler_pronostics(reponse, consultees, df):
    """Garde les sources vérifiables et calcule le consensus.

    Retourne {"sources", "ecartees", "ecartees_noms", "nb_consultees", "consensus", "alertes"} ;
    consensus trié par points,
    une entrée par cheval cité : {"num", "nom", "points", "citations", "premier"}.
    """
    noms = {str(int(n)): nom for n, nom in zip(df["NUM"], df["NOM"]) if str(n).isdigit()}
    domaines = {c["domaine"]: c for c in consultees}
    sources, ecartees, ecartees_noms, alertes = [], 0, [], []
    for src in (reponse or {}).get("sources", []) if isinstance(reponse, dict) else []:
        if not isinstance(src, dict):
            continue
        dom = _domaine(src.get("site")) or _domaine(src.get("nom"))
        trouve = _source_consultee(src.get("site") or src.get("nom"), src.get("nom"), domaines)
        if trouve is None:
            ecartees += 1
            ecartees_noms.append(str(src.get("nom") or src.get("site") or "?"))
            continue
        selection, inconnus = [], []
        for n in src.get("selection", []) if isinstance(src.get("selection"), list) else []:
            num = _numero(n)
            if num in noms and num not in selection:
                selection.append(num)
            elif num and num not in noms:
                inconnus.append(num)
        if inconnus:
            alertes.append(f"{src.get('nom') or dom} cite des numéros absents ({', '.join(inconnus)}) : ignorés.")
        if selection:
            sources.append({"nom": str(src.get("nom") or dom), "domaine": trouve,
                            "url": domaines[trouve]["url"], "selection": selection[:5]})

    points = {}
    for src in sources:
        for rang, num in enumerate(src["selection"]):
            e = points.setdefault(num, {"num": num, "nom": noms[num], "points": 0, "citations": 0, "premier": 0})
            e["points"] += POINTS_RANG[rang]
            e["citations"] += 1
            e["premier"] += rang == 0
    consensus = sorted(points.values(), key=lambda e: (-e["points"], -e["citations"]))
    return {"sources": sources, "ecartees": ecartees, "ecartees_noms": ecartees_noms,
            "nb_consultees": len(domaines), "consensus": consensus, "alertes": alertes}


def texte_consensus(compil):
    """Résumé du consensus pour le prompt d'analyse ; None s'il n'y a aucune source."""
    if not compil or not compil["sources"]:
        return None
    n = len(compil["sources"])
    lignes = []
    for e in compil["consensus"]:
        ligne = f"n° {e['num']} {e['nom']} : {e['points']} pts, cité par {e['citations']}/{n} sources"
        if e["premier"]:
            ligne += f", 1er choix de {e['premier']}"
        lignes.append(ligne)
    return "\n".join(lignes)


# --- Historique ----------------------------------------------------------

COLONNES_HISTORIQUE = ["date", "hippodrome", "discipline", "profil", "pari", "chevaux",
                       "cote", "proba_ia", "gain_espere", "mise", "resultat", "gain_reel"]
RESULTATS = ["En attente", "Gagné", "Perdu"]


def ligne_historique(date, hippo, discipline, profil, pari):
    return {"date": date, "hippodrome": hippo, "discipline": discipline, "profil": profil,
            "pari": pari["type"], "chevaux": pari["num"], "cote": pari["cote"],
            "proba_ia": round(pari["proba_retenue"], 3), "gain_espere": round(pari["gain_espere"], 3),
            "mise": pari["mise"], "resultat": "En attente", "gain_reel": 0.0}


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
