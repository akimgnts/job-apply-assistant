# Accueil ciblé et radar fiable

Objectif : trois colonnes candidatures, contacts, offres ; retirer le panneau vert et les compteurs sans action. Respecter l'autorisation de réalisation autonome déjà donnée.

- Remplacer le scoring par mots-clés avec frontières de mots, pondération rôle/compétences/seniorité, sans bonus temporel. Un contenu incomplet doit afficher une confiance faible ; ne pas fabriquer une précision par des variations arbitraires.
- Utiliser posted_date puis first_seen_at/created_at pour la fraîcheur, jamais last_seen_at. Distinguer publication et découverte.
- API : offres actives par défaut, archives explicitement sélectionnables, fenêtre 24h/48h et tri récent/pertinent indépendants. Aucun effacement de données.
- API contacts paginée pour la colonne contacts ; candidatures en préparation filtrées côté serveur.
- Interface : trois colonnes blanches compactes, radar avec cartes riches (entreprise, lieu, date, justification, action) et onglets actives/archives. États vides honnêtes.
- Maintenir les archives dans l'échantillon marché, même en présence d'analyses de candidatures.
- Vérifier avec tests de non-régression scoring, temporalité, isolation archives/actives, contacts et analyse marché ; puis vérifier les vues dans le navigateur.

## Vérification du 20 septembre

Réalisé : accueil en trois colonnes, score indépendant de la fraîcheur et avec limites explicites, dates de publication/découverte, fenêtres horaires, tri, API contacts, archivage séparé, analyse combinée sans doubler les URLs déjà analysées.

42 tests passent ; syntaxe JavaScript et diff vérifiés. Contrôle navigateur : accueil, archives (12 cartes/page), filtre 48 h, remise à zéro, détail de l'offre et console sans erreur. État réel vérifié : 0 offre active, 642 archives, aucun contact. Mon évolution utilise 641 offres stockées + 1 candidature analysée. Aucune archive réactivée artificiellement.
