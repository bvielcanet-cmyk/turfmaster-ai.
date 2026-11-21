# TurfMaster

Application Streamlit qui analyse une liste de partants avec Gemini et ne conseille un pari
**que lorsque son intérêt est mesurable** par rapport à votre profil de risque.

> Les probabilités sont des estimations de l'IA, pas une garantie. L'onglet **Historique**
> permet de vérifier, course après course, si les pronostics rapportent vraiment.

## Utilisation

**Le plus simple : 📅 Programme PMU.** Choisissez le jour et la course : partants, cotes PMU du
moment, hippodrome et discipline sont chargés automatiquement. Le copier-coller reste disponible
(📋), par exemple si le site du PMU ne répond pas.

> Les données viennent du site du PMU. Ce n'est pas une interface officiellement ouverte au
> public : elle peut changer sans prévenir. L'application l'interroge avec modération.

Pour le copier-coller :

1. Dans la barre latérale : hippodrome, discipline, capital et profil de risque.
2. Collez les partants. Deux formats sont acceptés :

   - **le copier-coller du tableau des partants d'un site de courses**, tel quel (numéro seul,
     puis nom, jockey - entraîneur, sexe/âge, poids, musique et cote) :

     ```
     1
     ISISDELAGARDE
     Zuliani L. - Lagarde F.
         H/8   69 kg   2s 5s 1s (25) 3s 2s 2s   6.5
     2
     FENOMENE D'OC
     ...
     ```

   - **un cheval par ligne** : `NUMÉRO NOM [FERRURE] [MUSIQUE] [COTE]`

     ```
     12 FAKIR D4 1a 2a 4.5
     3 ÉCLAIR DE LUNE DA 1a 12,5
     ```

   Les lignes non reconnues sont signalées. La cote (avec un point ou une virgule) est facultative.
   La discipline est devinée d'après la musique (`a`/`m` trot, `p` plat, `h`/`s`/`c` obstacles)
   si elle est sur « Auto ».
3. Cliquez sur **⚡ ANALYSER LA COURSE**. Si un pari est conseillé, **💾 Enregistrer le ticket**.
4. Après la course, dans **📊 Historique**, indiquez *Gagné* ou *Perdu* et la somme rapportée.

### Quand l'application conseille-t-elle de jouer ?

Un pari n'est conseillé que si son intérêt peut être **mesuré** :

1. **Il faut la cote de chaque partant.** Sinon : « 🚫 Pas de pari », cote manquante.
2. **Probabilité retenue** = moyenne entre l'estimation de l'IA et celle des cotes (marge des
   opérateurs retirée). L'IA peut se tromper, surtout sur les petites probabilités : on ne lui
   fait confiance qu'à moitié.
3. **Gain espéré** pour 1 € misé en Simple Gagnant = probabilité retenue × cote − 1.
4. Le pari est conseillé seulement si **toutes** les conditions du profil sont remplies :

| Profil | Gain espéré | Probabilité | Cote | Mise maximale |
|---|---|---|---|---|
| Prudent | ≥ +10 % | ≥ 30 % | ≤ 4 | 1 % du capital |
| Équilibré | ≥ +8 % | ≥ 15 % | ≤ 10 | 2 % du capital |
| Offensif | ≥ +5 % | ≥ 8 % | ≤ 20 | 4 % du capital |

5. **Mise** = fraction du critère de Kelly (¼ en Prudent et Équilibré, ½ en Offensif),
   plafonnée comme ci-dessus : plus l'écart avec les cotes est grand, plus la mise l'est.
6. **Limite de pertes** sur 7 jours (100 € par défaut, réglable) : la mise est réduite puis
   bloquée quand elle est atteinte. Les tickets en attente comptent. Nécessite l'historique.

Les cotes bougent jusqu'au départ : l'application indique la **cote minimale** en dessous de
laquelle le pari n'a plus de valeur.

Les paris combinés (Trio, Couplé…) proposés par l'IA sont affichés comme idée, **sans mise** :
leur gain ne peut pas être mesuré sans leurs rapports.

Les numéros renvoyés par Gemini sont vérifiés : un numéro absent du départ est écarté et signalé.

### Pronostics de la presse

L'option **📰 Pronostics de la presse** cherche les pronostics publiés pour la course
(presse hippique, sites de pronostics) et les compile :

- **seules les sources réellement consultées par la recherche Google sont gardées** ; une source
  citée par l'IA mais introuvable dans les pages consultées est écartée (risque d'invention) ;
- les numéros absents du départ sont ignorés et signalés ;
- **consensus** : 1er choix d'une source = 5 points, 2e = 4 … 5e = 1 ;
- le consensus est transmis à l'IA comme un avis parmi d'autres, et affiché dans le verdict
  (« cité par 3 sources sur 5 ») et le classement. **Il ne déclenche jamais un pari à lui
  seul** : la règle de valeur mesurable reste la même.

Cette recherche tourne en même temps que celle de la météo et est gardée 3 h par course.

> **Quota Gemini gratuit** : la clé gratuite est limitée à **20 requêtes par jour** pour
> `gemini-2.5-flash`. Une analyse complète en utilise jusqu'à 3 (météo, pronostics, analyse),
> soit environ 6 courses par jour. Désactivez les recherches dans la barre latérale pour en
> analyser davantage (1 requête par course), ou passez à une clé payante.

### Recherche Google

L'option **🔎 Recherche Google** cherche la météo, le terrain et les distances du jour. Elle est
faite **une fois par hippodrome et par jour** puis réutilisée : seule la première course de la
réunion est plus lente. Si elle n'est pas disponible, l'analyse se fait sans et un message
l'indique. Une même course n'est envoyée qu'une fois par heure à Gemini.

### Mesurer la précision de l'IA

**Chaque analyse est enregistrée**, qu'un pari soit conseillé ou non, avec les probabilités de
l'IA et celles des cotes pour chaque partant. Dans l'onglet **📊 Historique** :

1. **🔄 Récupérer les arrivées** : pour les courses du programme PMU, le gagnant et le rapport
   officiel sont récupérés au PMU (sans requête Gemini). Pour les courses collées, cochez la
   recherche Gemini (1 requête par course, résultat non officiel). Les tickets joués sont
   remplis automatiquement (Gagné / Perdu, somme rapportée).
2. **📏 L'IA prévoit-elle mieux que les cotes ?** L'application compare l'IA et les cotes sur
   les courses terminées (perte logarithmique, score de Brier, part des favoris gagnants).
3. **Réglage automatique** : à partir de **30 courses mesurées**, la part de l'IA dans la
   probabilité retenue n'est plus fixée à 50 % mais réglée sur la valeur qui a le mieux prévu
   les gagnants. Si les cotes font mieux, elle peut descendre jusqu'à 0 % : l'application ne
   conseillera alors plus de paris basés sur l'avis de l'IA.

**Pour faire avancer la mesure vite** : le bouton **🧪 Tester l'IA sur 5 courses passées** analyse
5 courses françaises des 7 derniers jours (5 requêtes Gemini), sans recherche internet pour que l'IA
ne puisse pas trouver le résultat, et les enregistre avec leur arrivée officielle. Une course déjà
testée n'est jamais refaite. On peut aussi analyser à la main une course terminée du programme PMU.

**Ce qu'a montré un test sur 560 courses PMU** (7 au 20 novembre 2026) : les cotes au départ sont
très bien calibrées (quand elles donnent 25 %, le cheval gagne environ 25 % du temps) ; les corriger
n'apporte presque rien. En revanche, miser sur les chevaux cotés **au-delà de 20** a perdu 29 à 58 %
de la mise, contre 8 à 16 % en dessous : la cote maximale du profil Offensif est donc de 20.

Sans Google Sheets, analyses et tickets sont gardés dans des fichiers locaux (`donnees_locales/`) :
sur Streamlit Cloud, ils sont **perdus à chaque redémarrage**. Configurez Google Sheets (ci-dessous)
pour les garder. Les onglets `TurfMaster` (tickets) et `Analyses` sont créés automatiquement.

## Configuration (Secrets)

Sur Streamlit Cloud : *Settings → Secrets*. En local : fichier `.streamlit/secrets.toml`
(à ne jamais publier sur GitHub).

```toml
[gemini]
api_key = "VOTRE_CLE_GEMINI"
```

### Historique Google Sheets (facultatif)

Sans cette section, l'application fonctionne mais tickets et analyses sont gardés dans des fichiers locaux, perdus à chaque redémarrage sur Streamlit Cloud.

1. Dans Google Cloud, créez un **compte de service**, activez les API *Google Sheets* et
   *Google Drive*, puis téléchargez sa clé JSON.
2. Partagez votre Google Sheet avec l'adresse du compte de service (`...@...iam.gserviceaccount.com`),
   en **Éditeur**.
3. Ajoutez dans les Secrets (valeurs reprises du fichier JSON) :

```toml
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/VOTRE_ID/edit"
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Les tickets sont rangés dans un onglet **TurfMaster**, créé automatiquement : les autres
onglets du classeur ne sont pas touchés. `test_diag.py` permet de vérifier la connexion.

## Versions

Les versions des bibliothèques sont fixées dans `requirements.txt` : une mise à jour de
Streamlit ne peut pas casser l'application sans prévenir. Pour les mettre à jour, changez les
numéros, lancez les tests, puis publiez.

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests simulent Gemini et Google Sheets : ils ne consomment aucun quota.
Ils sont lancés automatiquement par GitHub Actions à chaque envoi.

## Organisation du code

- `app.py` : interface Streamlit
- `turf_logic.py` : lecture des partants, décision de pari, appels Gemini, statistiques
- `pmu.py` : programme, partants, cotes, arrivées et rapports du PMU
- `mesure.py` : enregistrement des analyses, précision de l'IA face aux cotes
- `tests/` : tests automatiques
