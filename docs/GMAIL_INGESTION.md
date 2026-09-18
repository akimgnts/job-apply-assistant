# Gmail dans la première interface Job Apply

Le suivi est intégré à **Mes candidatures → Suivi & Gmail** (`/#applications?view=tracking`). L’onglet Préparation conserve les analyses et documents. Les dossiers, messages et échéances sont servis par la même API FastAPI et protégés par le même `WEB_ACCESS_TOKEN`. Aucun second serveur React ni seconde clé d’accès n’est nécessaire.

## Installation

1. Installer les dépendances de `requirements.txt` dans l’environnement Python 3.11 du projet.
2. Pour une nouvelle base SQLite locale, `scripts/run_web.sh` initialise les tables explicitement. Pour une base existante gérée par Alembic, sauvegarder puis appliquer `alembic upgrade head` dans son environnement habituel. La nouvelle chaîne suit `107133a6b922 → web_outreach_20260917 → gmail_tracking_20260917` ; elle ne réutilise pas la migration Gmail Stage 1 `009` (déjà occupée par Radar). Ne pas appliquer cette chaîne directement à une base issue d’une autre branche sans vérifier sa révision.
3. Configurer un client OAuth Google de type application de bureau avec Gmail API activée ; déposer son fichier dans `credentials.json` (ignoré par Git).
4. Exécuter `python -m app.services.gmail_oauth`, puis autoriser la lecture de la boîte Google choisie. Cette étape reste une autorisation explicite de l’utilisateur.
5. Activer `GMAIL_ENABLED=true` dans `.env` et redémarrer le serveur. `WEB_USER_ID` sélectionne le propriétaire des dossiers **et** du suivi Gmail. Par défaut : `local`. Pour les dossiers Telegram, utiliser l’identifiant Telegram correspondant.

Variables facultatives : `GMAIL_CREDENTIALS_FILE`, `GMAIL_TOKEN_FILE` (JSON uniquement), `GMAIL_SEARCH_QUERY`, `GMAIL_SCHEDULER_ENABLED=false`, `GMAIL_INGESTION_INTERVAL_MINUTES=30`. Le scheduler ne démarre que si Gmail et le scheduler sont activés. Un seul hôte doit effectuer les synchronisations, le verrou étant local au système de fichiers.

## Fonctionnement

- Lecture seule Gmail : aucun envoi, suppression ou changement de lecture.
- Import limité à trois pages de cent messages par exécution ; le bouton Continuer l’import reprend le curseur conservé. Déduplication par espace, boîte et identifiant Gmail.
- Classification proposée et association validée manuellement. Un fil déjà associé peut suggérer sa candidature, mais les nouveaux messages restent à vérifier.
- Accusés de réception distincts des réponses de recruteurs ; entretiens, refus et réponses validés actualisent le suivi sans modifier le statut de préparation du dossier.
- Relances affichées et saisies dans le fuseau local, conservées en UTC ; aucune relance automatique envoyée.
- Les contenus d’emails sont affichés comme texte échappé. Les tokens OAuth JSON sont enregistrés avec des droits privés ; les anciens fichiers pickle ne sont pas chargés.

La démonstration sur le port 8768 utilise une base dédiée dans `/tmp`, des dossiers fictifs et Gmail désactivé. Elle n’utilise pas la boîte réelle ni la base de travail.

## Vérification

`DATABASE_URL=sqlite:// APP_ENV=test PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_gmail_tracking.py tests/test_tracking_api.py tests/test_web_access.py tests/test_web_api.py tests/test_web_bootstrap.py -q`

Les tests n’appellent pas Google. La connexion OAuth réelle reste à vérifier après autorisation du compte.
