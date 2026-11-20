# TurfMaster

Application Streamlit qui analyse une liste de partants avec Gemini et propose un ticket
(classement des 5 chevaux, outsider, type de pari, mise).

> Les probabilités sont des estimations de l'IA, pas une garantie. L'onglet **Historique**
> permet de vérifier, course après course, si les pronostics rapportent vraiment.

## Utilisation

1. Dans la barre latérale : hippodrome, discipline, capital et profil de risque.
2. Collez les partants, un par ligne : `NUMÉRO NOM [FERRURE] [MUSIQUE] [COTE]`

   ```
   12 FAKIR D4 1a 2a 4.5
   3 ÉCLAIR DE LUNE DA 1a 12,5
   8 JOE 3m
   ```

   Les lignes non reconnues sont signalées. La cote (avec un point ou une virgule) est facultative.
3. Cliquez sur **⚡ GÉNÉRER LE TICKET GAGNANT**, puis **💾 Enregistrer le ticket** pour le garder.
4. Après la course, dans **📊 Historique**, indiquez *Gagné* ou *Perdu* et la somme rapportée.

### Mise

La mise est calculée par l'application, pas par l'IA :

| Profil | Mise | Type de pari demandé |
|---|---|---|
| Prudent | 1 % du capital | Simple Placé, Couplé Placé |
| Équilibré | 2 % du capital | Couplé Gagnant, Trio, Couplé Placé |
| Offensif | 4 % du capital | Trio Ordre, Quarté+, Quinté+ |

### Recherche Google

L'option **🔎 Recherche Google** laisse Gemini chercher la météo, le terrain et les cotes du jour.
Si elle n'est pas disponible pour votre clé (ou si son quota est épuisé), l'analyse est
refaite automatiquement sans recherche et un message l'indique.

Une même course (mêmes partants et réglages) n'est envoyée qu'une fois par heure à Gemini :
la réponse est réutilisée, ce qui économise le quota.

## Configuration (Secrets)

Sur Streamlit Cloud : *Settings → Secrets*. En local : fichier `.streamlit/secrets.toml`
(à ne jamais publier sur GitHub).

```toml
[gemini]
api_key = "VOTRE_CLE_GEMINI"
```

### Historique Google Sheets (facultatif)

Sans cette section, l'application fonctionne mais l'historique est désactivé.

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
- `turf_logic.py` : lecture des partants, mise, appel Gemini, statistiques
- `tests/` : tests automatiques
