# Test utilisateur du 15 novembre 2026

## Parcours et constats

- Accès et API : service prêt, authentification de la session existante et API protégée fonctionnelles.
- Radar : 4 304 offres conservées, dont 2 661 actives et 1 643 archivées. Une archive Business France pouvait passer dans le filtre actif : corrigé.
- Fraîcheur : dernière publication Business France observée en base le 13 novembre, dernière observation le 14 novembre. APEC : publication et observation les plus récentes au 1er octobre. Un appel limité du collecteur APEC a retourné HTTP 403. Une observation n'est pas une garantie de collecte complète.
- Préparation : dossier Indeed Crédit Agricole Business Digital importé, analyse 8/10, CV/lettre/email générés. Les versions de documents gonflaient le compteur et un dossier partiel était présenté comme prêt : corrigé. Les versions antérieures restent en base.
- Documents : aperçu HTML fonctionnel, endpoint PDF du CV testé en production : HTTP 200, signature PDF valide, 44 611 octets. La qualité éditoriale reste à examiner document par document ; le service utilise encore un contenu de secours lors d'une réponse IA invalide.
- Gmail : historique disponible, connexion expirée (RefreshError), dernière synchronisation le 25 septembre. Renouvellement de l'autorisation nécessaire ; aucune connexion rétablie annoncée. Le pipeline affiche maintenant cet état.
- Brouillons : le lien ouvrait le dashboard faute de page enregistrée. Une page dédiée expose désormais les derniers emails de candidature et les brouillons de contact. Elle précise que ces textes ne sont pas nécessairement des brouillons Gmail.
- Entreprises : 1 338 contacts, source et statut de vérification visibles. Certains contacts n'ont pas d'adresse et certains sont des boîtes de candidature ; leur présence ne signifie pas qu'il s'agit d'un interlocuteur direct vérifié.
- Mon évolution : rapports et historique disponibles. Des lacunes rapportées par les analyses contredisaient des blocs de profil vérifiés. Ces cas deviennent des actions de clarification du niveau et de valorisation de preuves, sans présumer une absence de maîtrise.
- Profil : source Master V4 côté génération ; certains intitulés de présentation et anciens blocs mentionnent encore V3. L'harmonisation et la traçabilité de la source restent à terminer.
- Assistant : présent dans l'interface et relié aux ressources. La pertinence de ses réponses, la couverture de ses actions et sa résistance aux faux faits demandent des évaluations dédiées ; aucun verdict global de fiabilité n'est donné ici.

## Corrections de cette passe

1. Radar actif strict, archives accessibles pour l'analyse.
2. Fenêtres de publication 24 h / 48 h / 7 jours et dates de fraîcheur par source.
3. Comptage par type de document, dernière version non vide et signalement d'un dossier incomplet.
4. Génération partielle distinguée d'un dossier complet et préservation des statuts après envoi.
5. Connexion Gmail expirée visible depuis la préparation.
6. Page de brouillons effectivement accessible.
7. Plan d'action confronté aux blocs vérifiés du profil.
8. Contrat de sortie de la lettre explicité : quatre paragraphes, langue source, URLs absolues.

## Points restant à traiter

- Restaurer un accès autorisé et stable à APEC ; le 403 n'est pas contourné.
- Renouveler OAuth Gmail puis vérifier la synchronisation et les liens avec les dossiers.
- Rendre le recours au contenu de secours visible et évaluer les CV/lettres avec des exemples validés.
- Réconcilier les anciens doublons de dossiers et les entreprises/intitulés imprécis, en conservant les preuves et l'historique.
- Évaluer l'assistant sur des questions factuelles et vérifier l'affichage mobile des PDF et documents longs.

Aucune candidature ni aucun message n'a été envoyé à un recruteur pendant cette passe.
