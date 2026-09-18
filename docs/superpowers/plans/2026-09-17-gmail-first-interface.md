# Gmail dans la première interface

Objectif : intégrer le suivi Gmail à l’interface verte Job Apply du workspace jobapply, comme demandé par l’utilisateur. Conserver la préparation des dossiers ; ajouter les onglets Préparation et Suivi & Gmail à Mes candidatures.

Architecture : mêmes FastAPI et authentification WEB_ACCESS_TOKEN, même propriétaire WEB_USER_ID. Réutiliser le moteur Gmail en lecture seule, ses validations manuelles et son verrou de synchronisation. Migration dédiée à cette branche ; aucune migration de production automatique.

- [x] Porter les modèles, services, migration et tests Gmail ; aligner accès et propriétaire.
- [x] Ajouter le suivi, la boîte des messages, les détails et les relances dans le style existant.
- [x] Exécuter les tests web/Gmail et vérifier dans le navigateur sur une base de démonstration isolée.

Validation : 30 tests web/Gmail passent, JavaScript vérifié avec node --check. Parcours navigateur : association confirmée, compteur de réponses actualisé, échéance saisie puis persistée. Rendu mobile et bureau sans débordement horizontal observé. Gmail réel non connecté.
