# Agent de candidature dans Chrome

## Intention

Réduire le temps entre une offre pertinente et une candidature préparée, en réutilisant le profil source, les agents de génération, les PDF et le suivi existants. L'extension agit à la demande sur le formulaire ouvert. Une soumission automatique générale n'est pas livrée dans cette première version : l'utilisateur relit les réponses et soumet depuis le site.

## Choix d'architecture

Un panneau latéral MV3 est préféré à un bot serveur qui se connecterait aux job boards : le candidat conserve ses connexions, voit le formulaire et peut répondre aux questions imprévues. Un simple presse-papiers demanderait encore de ressaisir chaque champ. Le panneau lit le DOM via activeTab et scripting ; il ne reçoit pas de commandes depuis la page du recruteur.

Le panneau utilise un onglet Job Apply déjà authentifié comme relais pour les API. Le code injecté côté Job Apply fait des requêtes de même origine avec la session existante. La liste des chemins accessibles est fermée. Aucun jeton ni mot de passe supplémentaire n’est copié dans l’extension. Aucune politique CORS ou de protection des écritures existante n’est assouplie.

## Parcours

Offre ouverte → dossier existant ou import explicite → préparation des pièces manquantes → lecture du formulaire → plan de réponses → relecture/modification → application aux champs → dépôt du PDF choisi → relecture finale et soumission depuis le site → confirmation du statut dans Job Apply.

Le backend propose d'abord les réponses d'identité déterministes. Les textes libres passent par un agent borné au Master CV et à l'analyse du dossier sélectionné ; une preuve exacte du profil est requise. Les champs inconnus, personnels ou déjà renseignés sont signalés. Aucune valeur préexistante du formulaire n'est transmise à Job Apply.

## Erreurs et limites

Une session expirée demande une reconnexion à Job Apply. Une panne IA laisse les questions ouvertes non renseignées. Une navigation, un changement d'onglet cible ou de libellé empêche l'application d'un ancien plan. Les formulaires intégrés, composants personnalisés et étapes nouvelles sont traités comme des limites explicites, pas comme une réussite implicite.

## Validation

Tests unitaires du plan, de l'isolation utilisateur et du comportement DOM. Vérifications syntaxiques et du manifeste. Installation Chrome et tests de formulaires réels requis avant validation complète ; aucune candidature de test n'est envoyée à une entreprise.
