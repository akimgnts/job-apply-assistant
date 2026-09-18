# Job Apply — espace de candidature

L'utilisateur délègue explicitement les décisions et demande une réalisation autonome. Base : feature/job-market-radar (7448ea2), isolée sur codex/interface-jobapply. Aucune interface web existante sur les branches examinées. FastAPI ne fournit que deux réponses JSON.

## Choix
Une interface légère servie par FastAPI réutilise les agents et les modèles. Une SPA avec un second serveur introduirait un déploiement inutile ; un simple habillage Telegram ne couvrirait pas le Radar. Navigation persistante, français, fond ivoire, accent vert profond, typographie système, cartes nettes, listes denses lisibles, fiche latérale, formulaires accessibles, responsive.

## Parcours
Tableau de bord avec vrais compteurs et étapes ; Radar avec recherche, filtres, pagination, détail et sauvegarde ; candidatures avec statut, analyse et génération ; documents consultables et téléchargeables ; entreprises et contacts sourcés ; profil fondé sur les blocs et le Master CV ; intelligence carrière ; configuration lisible sans exposer de secrets. Import explicite des archives CSV du dépôt pour une installation locale, clairement datées et jamais présentées comme fraîchement collectées.

## Contrat
API /api : overview, offers, offers/{id}, offers/{id}/save, applications, applications/{id}, applications/{id}/analyze, applications/{id}/generate, documents, documents/{id}/download, companies, companies/{id}, profile, intelligence, settings, import-snapshot. Les collections sont {items,total,page,page_size}. Les mutations valident les entrées et renvoient des erreurs françaises. Profil mono-utilisateur configurable WEB_USER_ID. Pas d'envoi de candidatures ou messages automatique.

## Exploitation
PostgreSQL existant en production. SQLite explicitement configuré uniquement pour développement local ; aucune migration distante ni initialisation implicite à l'import du serveur. Clé d'accès si exposé hors loopback ; téléchargement protégé, contenu HTML isolé. IA indisponible explicitement signalée sans faux résultats. Tests API sur base isolée, vérifications navigateur desktop/mobile et tests existants sélectionnés.
