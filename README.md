# Espace membres — Caisse Elmoutahalivin

Application Streamlit avec connexion par identifiant/mot de passe (sans email), affichant à chaque membre sa situation personnelle + le tableau de bord global de la caisse. Les données sont lues automatiquement depuis le fichier Excel sur OneDrive.

## Déploiement sur Streamlit Community Cloud (gratuit)

### 1. Créer un dépôt GitHub
- Crée un compte sur https://github.com si besoin (gratuit)
- Crée un nouveau dépôt **privé** (important, car il contiendra les identifiants hashés)
- Mets-y tout le contenu de ce dossier **sauf** `IDENTIFIANTS_PRIVES_NE_PAS_PARTAGER.csv` et `.streamlit/secrets.toml` (déjà exclus par le `.gitignore` fourni)

### 2. Déployer
- Va sur https://share.streamlit.io et connecte-toi avec ton compte GitHub
- Clique "New app", choisis ton dépôt, la branche, et `app.py` comme fichier principal
- Avant de cliquer "Deploy", ouvre "Advanced settings" → "Secrets" et colle :
```toml
onedrive_url = "COLLE_ICI_TON_LIEN_ONEDRIVE"
```
- Clique "Deploy". Au bout d'une à deux minutes, l'app est en ligne avec une URL du type `https://xxxxx.streamlit.app`

### 3. Distribuer les accès
- Envoie l'URL de l'application à tous les membres
- Distribue-leur individuellement leur identifiant/mot de passe depuis `IDENTIFIANTS_PRIVES_NE_PAS_PARTAGER.csv` (par message privé, pas dans le groupe public)
- Le compte admin (`admin`) te donne accès à un onglet de gestion supplémentaire

## Lien OneDrive

Le lien doit être un lien de partage **"Toute personne disposant du lien"** (lecture seule suffit) vers le fichier `.xlsx`. L'application le convertit automatiquement en lien de téléchargement direct et rafraîchit les données toutes les 15 minutes.

## Tester en local avant de déployer

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# édite .streamlit/secrets.toml et colle ton lien OneDrive
streamlit run app.py
```

## Si la liste des membres change

Relance :
```bash
python generate_credentials.py chemin/vers/fichier.xlsx
```
Cela régénère `data/credentials.csv` (à committer) et un nouveau `IDENTIFIANTS_PRIVES_NE_PAS_PARTAGER.csv` (à ne jamais committer — attention à ne pas écraser les mots de passe déjà distribués sans prévenir les membres concernés).

## Sécurité — à savoir

- Les mots de passe sont à 4 chiffres et stockés hashés (jamais en clair) dans `data/credentials.csv`.
- C'est un niveau de sécurité adapté à un usage interne entre membres de confiance — pas un système bancaire. Ne mets pas d'informations plus sensibles que celles déjà présentes dans le fichier Excel.
- Le dépôt GitHub doit rester **privé**.
- Aucun nom de bénéficiaire d'aide n'apparaît dans l'application — uniquement les catégories d'aide et montants, comme pour les autres documents déjà fournis.

## Contenu du projet

- `app.py` — application principale (connexion, vues personnelle et collective)
- `auth.py` — logique de connexion
- `data_loader.py` — récupération et traitement du fichier Excel depuis OneDrive
- `generate_credentials.py` — script pour régénérer les comptes membres
- `data/credentials.csv` — identifiants (hashés) et logo
- `.streamlit/secrets.toml.example` — modèle pour le lien OneDrive
