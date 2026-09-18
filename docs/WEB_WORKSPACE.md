# Espace web Job Apply

L’interface française est servie par FastAPI avec les mêmes données et agents que le bot. Elle permet de consulter le Radar, sauvegarder les offres en candidatures, suivre leurs statuts, lancer une analyse, générer et télécharger les documents, consulter les entreprises, le profil et l’intelligence carrière. Aucun envoi de candidature ou de message n’est automatique.

## Démarrage local

Python 3.11 est requis. Depuis la racine du dépôt :

```bash
./scripts/run_web.sh
```

Le script crée `.venv` si nécessaire et installe les dépendances manquantes. Sans `DATABASE_URL` dans l’environnement ni dans `.env`, il configure explicitement `data/web_workspace.sqlite3`. Une configuration existante est conservée. Le serveur écoute sur [localhost:8000](http://localhost:8000) ; `PORT` permet de changer le port.

La création des tables et l’initialisation du profil sont réservées aux fichiers SQLite locaux. Le profil atomique Master V3 est ajouté uniquement si la table du profil est vide. Les modifications existantes ne sont jamais remplacées. Pour initialiser manuellement un fichier local :

```bash
DATABASE_URL=sqlite:///data/web_workspace.sqlite3 python -m app.web.bootstrap
```

L’import du serveur ne crée aucune table et ne lance aucune migration. Une base existante dont le schéma est ancien nécessite une migration préparée séparément.

## Archives du Radar

Pour charger volontairement les 642 offres de l’archive du **5 septembre 2026** :

```bash
./scripts/run_web.sh --import-snapshot
```

L’interface propose également une action explicite d’import des archives. Ces données proviennent de `exports/ats_job_offers_live.csv` ; il ne s’agit pas d’une collecte récente. Leurs dates originales sont conservées, leur source porte le préfixe `snapshot:` et leur statut est `archived`. Leur disponibilité actuelle n’est pas vérifiée. Aucun appel réseau n’est réalisé pendant cet import.

L’import est idempotent par URL : une offre déjà présente, notamment issue d’une collecte en direct, n’est jamais remplacée. Les entreprises sont déduites des champs `Company:` du texte source ou d’un registre d’URL connu, jamais des identifiants numériques exportés.

## Configuration et production

- `WEB_USER_ID` choisit le propriétaire mono-utilisateur des candidatures web ; sa valeur par défaut est `local`. Choisir l’identifiant Telegram existant pour retrouver ses candidatures.
- `WEB_ACCESS_TOKEN` protège l’espace lorsqu’il est configuré. Sans jeton, l’accès est limité au loopback. Un accès distant exige un jeton ; utiliser également HTTPS et une configuration réseau appropriée.
- `OPENAI_API_KEY` active les analyses et la génération IA. Sans clé utilisable, l’interface reste consultable et les actions IA signalent leur indisponibilité.
- `DATABASE_URL` sélectionne la base. PostgreSQL demeure la base de production ; SQLite est une option de développement local.
- Les secrets ne doivent jamais être committés ni exposés dans la configuration affichée.

Le script local ne lance **jamais Alembic** et ne crée aucune table sur PostgreSQL. Pour la production, conserver la procédure de migration existante : sauvegarde, validation sur une copie isolée, puis migration explicitement déclenchée. `python -m app.web.bootstrap` refuse PostgreSQL, les bases en mémoire et les URI SQLite spéciales.

## Vérification

```bash
DATABASE_URL=sqlite:///:memory: .venv/bin/python -m pytest tests/test_web_bootstrap.py tests/test_web_api.py -q
```

Les tests utilisent une base isolée et des appels IA simulés. Aucun service de production n’est requis.
