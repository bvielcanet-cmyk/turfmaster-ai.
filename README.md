# TurfMaster : aide à la décision

Application Streamlit qui aide à **comprendre une course** (qui a des chances, à quel point elle est
ouverte) et **ce que risque un pari** que vous avez choisi. Elle ne dit pas quoi jouer et ne conseille
aucune mise.

> **Aucun avantage sur les autres parieurs n'a été démontré.** Ne misez que ce que vous acceptez de
> perdre. Joueurs Info Service : 09 74 75 13 13 (appel non surtaxé).

## ⚠️ Correction du 22/11/2026 : les anciens résultats étaient faux

Les versions précédentes annonçaient un Simple Placé gagnant (+22 %, +11 %), une règle corrigée, des
simulations de mises, une protection du capital et un mode « one shot ». **Tout cela est retiré.**

Ces tests choisissaient les paris avec les cotes que le PMU renvoie pour une course terminée. Elles
étaient présentées comme « au départ » : ce sont les cotes de **clôture, publiées après le départ**.
Les paris testés étaient donc impossibles à jouer.

**Règle pour toute étude future : une donnée qui sert à choisir un pari doit être horodatée avant
le départ.** Les rapports officiels ne servent qu'au règlement.

## Ce que montre le test refait sans tricher

2 342 courses PMU du 22/09 au 20/11/2026, dont **1 774 retenues** : celles où chaque partant avait une
cote horodatée au moins 10 minutes avant le départ (30 en médiane). Les 568 autres, souvent de petites
réunions, ne sont pas couvertes. Seuils des feux et paris testés fixés avant de lire ces données.

| Favori | Courses | Gagne (calcul) | Gagne (réel) | Placé (calcul) | Placé (réel) | Trio désordre (réel, 8+ partants) |
|---|--:|--:|--:|--:|--:|--:|
| 🟢 claire | 481 | 47,4 % | 41,4 % | 78,2 % | 70,3 % | 12,5 % |
| 🟠 disputée | 709 | 27,6 % | 26,9 % | 58,6 % | 58,3 % | 6,7 % |
| 🔴 très ouverte | 584 | 17,9 % | 19,9 % | 43,1 % | 40,9 % | 4,5 % |

Le feu distingue bien les courses lisibles des courses ouvertes. Le calcul surestime les favoris des
courses claires, et sous-estime le trio des trois préférés : l'application affiche aussi le constat réel.

**Paris sur les chevaux préférés, 1 € par pari, rapports officiels :**

| Pari | Courses | Passe | Résultat | Intervalle à 90 % |
|---|--:|--:|--:|--:|
| Simple Placé | 1 774 | 56 % | −11,3 % | −14 à −8 % |
| Simple Gagnant | 1 774 | 29 % | −15,1 % | −21 à −9 % |
| Couplé Placé | 1 598 | 25 % | −15,6 % | −23 à −9 % |
| Couplé Gagnant | 1 598 | 13 % | −16,7 % | −27 à −5 % |
| 2 sur 4 | 1 311 | 31 % | −22,4 % | −28 à −16 % |
| Trio | 1 530 | 7 % | −27,8 % | −42 à −13 % |
| Couplé Ordre | 176 | 11 % | −46,8 % | −67 à −26 % |
| Super 4 | 423 | 2 % | −55,6 % | −86 à −16 % |
| Trio Ordre | 175 | 5 % | −61,4 % | −83 à −37 % |

Par couleur de feu, **aucun pari ne gagne de façon fiable** sur les deux périodes (sept.-oct. et
novembre). Seule case positive sur l'ensemble : le Super 4 des courses rouges, 36 courses et un seul
pari gagnant, donc du hasard. Multi, Tiercé, Quarté+, Quinté+ et Pick 5 ne sont pas testés, ni les
sélections autres que les chevaux préférés.

## Utilisation

- **🏇 La course** : le feu, le podium estimé d'après les cotes, le risque d'un pari que vous
  choisissez et, sur demande, l'avis de l'IA et de la presse. Tout est gratuit sauf cet avis.
- **🚦 Courses du jour** : toutes les courses françaises à venir, de la plus claire à la plus ouverte,
  sans requête Gemini.
- **📒 Mon carnet** : les paris réellement joués, leur résultat net et la comparaison IA / cotes.

| Feu | Chances du favori de gagner | Sens |
|---|---|---|
| 🟢 Course claire | au moins 35 % | un favori se détache |
| 🟠 Course disputée | de 22 à 35 % | un favori, de vrais rivaux |
| 🔴 Course très ouverte | moins de 22 % | surprise possible |

**Un feu vert ne veut pas dire « jouer »** : il mesure le suspense, pas la rentabilité.

Le **budget sur 7 jours** (barre latérale, à régler à chaque visite) compte tout ce qui a été misé :
un gain ne l'agrandit pas. C'est un avertissement, pas un blocage.

> Les données viennent du site du PMU. Ce n'est pas une interface officiellement ouverte au
> public : elle peut changer sans prévenir. L'application l'interroge avec modération.

Pour le copier-coller :

1. Choisissez **📋 Copier-coller** et indiquez l'hippodrome.
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
3. Le feu et le podium s'affichent dès que chaque partant a une cote.

### Avis de l'IA

Le bouton **🤖** demande un avis à Gemini, affiché à côté de celui des cotes. C'est une information :
il n'en est tiré ni pari ni mise. Les numéros inventés sont écartés et signalés.

### Pronostics de la presse

L'option **📰 Pronostics de la presse** cherche les pronostics publiés pour la course
(presse hippique, sites de pronostics) et les compile :

- **seules les sources réellement consultées par la recherche Google sont gardées** ; une source
  citée par l'IA mais introuvable dans les pages consultées est écartée (risque d'invention) ;
- les numéros absents du départ sont ignorés et signalés ;
- **consensus** : 1er choix d'une source = 5 points, 2e = 4 … 5e = 1 ;
- le consensus est transmis à l'IA comme un avis parmi d'autres, et affiché à côté du sien.

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

### Carnet et mesure de l'IA

- **🔄 Récupérer les arrivées** règle les paris aux rapports officiels du PMU. Un non-partant ou une
  course annulée est remboursé. Aucun gain n'est estimé.
- **📏** compare l'IA et les cotes sur les courses terminées. Cette mesure ne change rien aux affichages
  et ne choisit aucun pari.
- **🧪** analyse 5 courses passées (5 requêtes Gemini) sans recherche internet. Les cotes y sont celles
  de la clôture : cela compare l'IA aux parieurs, cela ne valide aucun pari.

Si un onglet Google Sheets n'a pas pu être lu, l'application refuse de le réécrire. L'ancien onglet
`ConseilsPlace` n'est plus utilisé ; il n'est ni modifié ni supprimé.

### 🚦 Feux du matin sur Telegram (facultatif)

`.github/workflows/feux.yml` envoie une fois par jour la lisibilité des courses, sans pari ni mise.
Secrets GitHub : `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`. Les secrets Google n'y sont pas utiles.

Les lancements planifiés de GitHub **ne sont pas fiables** : l'ancienne tâche « toutes les 10 minutes »
n'a tourné qu'une fois sur une centaine de passages prévus. Le message peut être en retard ou absent.
*Actions → Feux du jour → Run workflow* le lance à la main.

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

Le carnet est rangé dans l'onglet **TurfMaster** et les analyses dans **Analyses**, créés
automatiquement. `test_diag.py` permet de vérifier la connexion.

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
- `decision.py` : feux, podium estimé, risque d'un pari choisi
- `carnet.py` : paris joués, règlement officiel, budget
- `turf_logic.py` : lecture des partants, appels Gemini, presse
- `pmu.py` : programme, partants, cotes, arrivées et rapports du PMU
- `mesure.py` : précision de l'IA face aux cotes
- `feux_du_matin.py` : message Telegram du matin
- `tests/` : tests automatiques
