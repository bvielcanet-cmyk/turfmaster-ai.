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

### 🎯 Conseil Placé (gratuit, sans IA)

Pour une course du programme PMU, le bouton **🎯 CONSEIL PLACÉ** compare les chances de chaque cheval
de finir placé (déduites des cotes du Simple Gagnant par la formule de Harville) aux **cotes
probables du Simple Placé** publiées par le PMU. Quand un Placé paie plus que ses chances ne le
justifient (gain espéré ≥ +10 %, cote probable minimale ≤ 20), il est conseillé. Aucune requête
Gemini n'est utilisée.

**Test sur des courses passées** (règle fixée avant le test de confirmation, 1 € par conseil,
rapports officiels) :

| Période | Courses | Conseils | Placés | Rendement |
|---|---|---|---|---|
| 22/09 → 31/10/2026 (confirmation) | 1 189 | 299 | 50,5 % | **+22 %** (intervalle à 90 % : +6 % à +40 %) |
| 01/11 → 20/11/2026 | 728 | 180 | 48,9 % | +11 % |

Ce décalage entre les paris Gagnant et Placé est un phénomène connu des paris mutuels. Mais ce
sont des **résultats passés** : les cotes bougent jusqu'au départ (jouer dans les dernières minutes,
seulement si la cote minimale reste au-dessus du seuil indiqué), et les chances de placé calculées
sont optimistes (62 % prévus, 50 % réels). D'où une **mise fixe** (0,5 / 1 / 1,5 % du capital selon
le profil) plutôt qu'un dosage de Kelly.

**Suivi à blanc** : chaque conseil donné sur une course à venir est enregistré (onglet
`ConseilsPlace`) et réglé au rapport officiel par « Récupérer les arrivées ». L'Historique affiche
le bilan réel. **Attendez au moins 100 conseils réglés avec un rendement positif avant de miser.**

#### Choisir sa mise : les séries de pertes

Simulation (20 000 tirages) de 300 conseils, à partir des 479 résultats réels passés, en supposant
que le rendement passé se maintient :

| Mise par conseil | Capital médian (départ 100) | Fini en perte | Baisse en cours de route > 20 % | > 40 % |
|---|---|---|---|---|
| 0,5 % (Prudent) | 128 | 4 % | 0 % | 0 % |
| 1 % (Équilibré) | 162 | 4 % | 17 % | 0 % |
| 1,5 % (Offensif) | 200 | 5 % | 57 % | 2 % |
| 3 % | 338 | 7 % | 100 % | 45 % |

Environ un conseil sur deux est perdu, et il faut s'attendre à **7 pertes d'affilée** de temps en
temps. Au-delà de 1,5 % du capital par conseil, les baisses deviennent brutales.

#### Deux règles suivies en parallèle

- **Règle confirmée** (celle qui est conseillée) : formule de Harville classique.
- **Règle corrigée** (en essai, relevée seulement par le suivi automatique) : formule de Harville
  corrigée (coefficients 0,81 et 0,65 appris sur 1 195 courses), mieux calibrée. Sur les courses
  passées : moins de conseils, plus rarement placés mais mieux payés (+37 % puis +15 %). Elle n'a
  pas eu de test de confirmation : le suivi réel départagera les deux.

Les chances de placé affichées utilisent la formule corrigée, plus réaliste.

#### 🛡️ Protection automatique des mises

Les mises sont un pourcentage du **capital actuel** (capital de départ + résultats des tickets joués,
ou du suivi à blanc tant que vous ne jouez pas). **Dès que le capital est à plus de 15 % sous son plus
haut, toutes les mises sont divisées par deux** (conseil Placé, plan du jour, alertes Telegram),
jusqu'à ce qu'il remonte au-dessus de ce seuil.

Comparaison sur les 479 conseils Placé passés (cote Gagnant < 8, capital de départ 100) :

| Stratégie | Capital final | Pire baisse réelle | Risque de baisse > 20 % |
|---|---|---|---|
| 1 % fixe | 184 | 15 % | 9 % |
| **1 % + réduction après −15 %** | **184** | 15 % | **3 %** |
| 2 % + réduction | 290 | 22 % | 65 % |
| Kelly (0,5 à 3 %) | 471 | 35 % | 83 % |

La protection garde le gain et coupe les grosses chutes. Miser plus gros (ou selon Kelly) multiplie
le gain **et** les chutes, et suppose des probabilités exactes alors que ce ne sont que des
estimations. Ne cherchez jamais à « vous refaire » en augmentant les mises après des pertes.

### 📅 Plan du jour

L'onglet **📅 Plan du jour** passe au crible **toutes les courses françaises à venir** (environ
60, en 30 secondes, **sans aucune requête Gemini**) avec la règle Placé, retient les **3 plus
prometteuses** et répartit un **budget de 20 à 100 €** selon le profil :

| Profil | Paris retenus | Part max. par pari |
|---|---|---|
| Prudent | Placés à forte chance (≥ 45 % de placé, estimation corrigée) | 40 % |
| Équilibré | les 3 meilleurs Placés de la règle confirmée | 50 % |
| Offensif | idem + règle corrigée (en essai) | 60 % |

- Seuls les chevaux de **cote Gagnant < 8** entrent dans le plan principal : c'est là que la règle a
  fait ses preuves (cote 1-4 : +14 %, intervalle à 90 % +4 à +23 % ; 4-8 : +20 %). Classement par
  critère de Kelly (chances × rapport, sans privilégier les paris trop risqués).
- Mises au prorata de la valeur, arrondies à 0,50 € inférieur, au moins 2 € (mise de base du PMU),
  **jamais au-delà du budget** ni des pertes encore autorisées. On ne force pas un pari pour « tout
  jouer » : certains jours, il y aura moins de 3 paris, ou aucun.
- **🃏 Joker outsider** (option) : 10 % du budget sur le meilleur outsider (cote Gagnant ≥ 8) qui
  passe la règle Placé. **Non prouvé** : sur 58 conseils passés de ce type, résultats très variables
  (de 0 % à +112 % selon la tranche, marges d'erreur énormes). Ses résultats sont suivis à part.
- **🔄 Actualiser les cotes** des courses retenues, et **🔬 Approfondir avec l'IA** (1 requête Gemini
  par course) : avis informatif de l'IA sur chaque cheval retenu, qui ne change pas le pari.
- **Le plan est provisoire** : les cotes du Placé bougent beaucoup dans la journée. Reconfirmez
  chaque pari 5 à 10 minutes avant le départ (la cote Placé minimale doit rester au-dessus du seuil
  indiqué) ; les alertes Telegram le font automatiquement.

Le suivi automatique envoie aussi un **résumé du plan sur Telegram vers 11 h** (variables GitHub
facultatives : `BUDGET`, 50 € par défaut, et `JOKER` = `oui` pour l'inclure).

#### 🎯 Mode « one shot » (par défaut)

Le budget de 20 à 100 € est **joué une seule fois**, sans lien avec un capital : vous acceptez de le
perdre. Prudent et Équilibré : 3 Placés ; Offensif : 2.

- **Répartition optimisée** : les mises sont réparties pour **maximiser les chances de finir en
  gain** (plus sur le Placé le plus sûr), au lieu de parts égales. Sur 15 000 plans passés de 3
  Placés : 68 % finis en gain au lieu de 56 %, au même risque de tout perdre (10 %).
- **Feu tricolore**, selon le risque de tout perdre (calculé puis corrigé : le calcul brut est trop
  optimiste, réel ≈ 1,3 à 1,4 × calculé ; correction apprise sur sept.-oct., vérifiée sur novembre) :
  🟢 **jeu possible** (≤ 10 %), 🟠 **risque élevé** (≤ 25 %, à vous de décider), 🔴 **ne pas jouer
  aujourd'hui** (au-delà, ou moins de 2 Placés intéressants).
- Les chances de finir en gain ne sont pas annoncées plan par plan (le calcul ne distingue pas
  fiablement les bons plans des autres) : sur un feu vert, la moyenne observée est d'environ
  **2 sur 3**.
- Même au feu vert, environ 1 plan sur 12 perd tout et un tiers finissent en perte.

Le mode **📈 Dans la durée** garde le fonctionnement précédent (mises selon le capital et sa protection).

#### 🏁 Ordre d'arrivée estimé (information)

Pour chaque course retenue (et sous chaque conseil Placé), l'application affiche l'**ordre d'arrivée
estimé** d'après les cotes, avec pour chaque cheval ses chances de **gagner** et d'**être placé**.
C'est une indication des chevaux à surveiller, **pas un pari conseillé** : sur 1 782 courses passées
de 8 partants ou plus, le 1er estimé a gagné 30 % du temps, le vainqueur était parmi les 3 premiers
estimés 59 % du temps, mais le trio exact n'est sorti que 6,6 % du temps dans le désordre et
**1,9 % dans l'ordre** — et les paris combinés rendent beaucoup moins aux parieurs (Couplé ≈ 51 %
contre ≈ 78 % pour le Placé).

### 🤖 Suivi automatique et alertes Telegram

Le fichier `.github/workflows/suivi.yml` lance `suivi_auto.py` **toutes les 10 minutes de 10 h à
minuit** (GitHub peut retarder de quelques minutes). À chaque passage :

1. pour chaque course française qui part **dans 3 à 20 minutes**, le conseil Placé (règle confirmée
   et règle corrigée) est enregistré dans l'onglet `ConseilsPlace` du Google Sheet et envoyé sur
   **Telegram** ;
2. les conseils dont la course est terminée sont réglés au rapport officiel, avec un
   récapitulatif Telegram.

Le suivi à blanc avance ainsi sans intervention (environ 100 conseils en une semaine).

**Configuration** — sur GitHub : *Settings → Secrets and variables → Actions → New repository secret* :

| Secret | Valeur |
|---|---|
| `GSHEETS_CREDENTIALS` | tout le contenu du fichier JSON du compte de service Google |
| `GSHEETS_URL` | l'adresse du classeur (`https://docs.google.com/spreadsheets/d/…/edit`) |
| `TELEGRAM_BOT_TOKEN` | le jeton du bot donné par @BotFather |
| `TELEGRAM_CHAT_ID` | l'identifiant de votre conversation avec le bot |

Pour trouver `TELEGRAM_CHAT_ID` : envoyez un message à votre bot, puis ouvrez
`https://api.telegram.org/bot<JETON>/getUpdates` et relevez le nombre après `"chat":{"id":`.

Facultatif, onglet *Variables* : `CAPITAL` (1000 par défaut) et `PROFIL` (`Équilibré` par défaut)
pour la mise indiquée dans les alertes. Sans `GSHEETS_CREDENTIALS`, le script tourne « à sec » et
n'enregistre rien. Les secrets ne sont jamais affichés dans les journaux de GitHub.

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
- `place.py` : conseil Simple Placé (formule de Harville), suivi à blanc
- `suivi_auto.py` : relevé automatique des conseils Placé et alertes Telegram (GitHub Actions)
- `plan.py` : plan du jour (crible, sélection, répartition du budget, joker)
- `protection.py` : capital actuel et réduction des mises après une baisse
- `tests/` : tests automatiques
