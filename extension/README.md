# Job Apply — Agent candidature Chrome (0.1, version à tester)

Cette extension relie le formulaire ouvert au dossier Job Apply. Elle prépare et remplit les champs standards, propose des textes sourcés et joint le CV ou la lettre en PDF. Elle ne soumet pas une candidature et ne déclare jamais un envoi qui n'a pas été confirmé.

## Installation locale

1. Ouvrir `chrome://extensions`, activer le mode développeur.
2. Choisir **Charger l’extension non empaquetée**, puis ce dossier `extension` (ou le dossier obtenu en décompressant le ZIP).
3. Épingler l’extension. Se connecter au site Job Apply dans un autre onglet du même profil Chrome et le laisser ouvert.
4. Ouvrir l’offre ou son formulaire de candidature et cliquer sur l’icône Job Apply. Le panneau latéral s’ouvre.

L’extension n'est pas encore publiée sur le Chrome Web Store. Son installation et son essai dans le vrai navigateur restent nécessaires avant de la considérer validée sur un job board.

## Utilisation

1. **Connecter mon espace**, puis sélectionner le dossier correspondant à l’offre. Si l’offre n’existe pas encore, renseigner entreprise/poste et utiliser **Importer cette offre** sur la page contenant l’annonce complète. Ne pas importer un formulaire vide à la place de l’annonce.
2. **Préparer les pièces manquantes** réutilise l’analyse et les agents de génération existants. Relire le dossier dans l’interface Job Apply. Une pièce déjà présente n’est pas régénérée.
3. Sur le formulaire, **Lire et proposer les réponses**. Les libellés visibles sont envoyés à Job Apply, jamais les valeurs déjà saisies. Le serveur utilise le Master CV et l’analyse du dossier. Les questions ouvertes peuvent utiliser le fournisseur IA déjà configuré dans Job Apply.
4. Corriger les propositions dans le panneau, puis **Valider et remplir ces champs**. Les preuves citées permettent de vérifier leur origine ; elles ne remplacent pas une relecture.
5. Choisir CV ou lettre et le champ de dépôt, puis **Joindre ce document**. Cela transmet le PDF au site du recruteur. Le document provient uniquement du dossier choisi.
6. Compléter les éléments restants et poursuivre les étapes du site. Relancer la lecture à chaque nouvelle étape. Cliquer à nouveau sur l’icône après un changement de domaine.
7. Soumettre depuis le job board après relecture. Une fois l’envoi confirmé par le site, utiliser **Marquer candidaté** dans Job Apply.

## Périmètre réel

- Champs HTML standards : nom, prénom, email, téléphone, LinkedIn, GitHub, portfolio ; textes longs proposés lorsque des preuves du profil sont validées.
- Fichiers : un PDF à la fois, dans un champ de dépôt standard choisi explicitement, limite de 15 Mo.
- Conserve les champs déjà remplis. Aucun clic automatique sur « Envoyer », aucun CAPTCHA traité, aucun accord coché.
- Les radios, sélecteurs sans correspondance certaine, menus personnalisés, champs dans des iframes tierces ou des Shadow DOM fermés demandent une saisie manuelle. Cette première version ne prétend pas couvrir tous les ATS.
- Les questions de salaire, visa, droit au travail, disponibilité, données personnelles sensibles et consentement restent à confirmer.
- Aucun accès permanent à tous les sites : `activeTab` permet la lecture du site sur lequel l’utilisateur invoque l’extension. Les permissions permanentes sont limitées aux espaces Job Apply listés dans le manifeste.
- Aucun mot de passe, jeton, profil ou PDF n'est conservé dans le stockage de l’extension. Seul l’identifiant temporaire de l’onglet cible est gardé pendant la session.

## Vérifications

Backend : `python -m pytest tests/test_form_filling_agent.py -q`

Formulaire : `node --test extension/form.test.cjs`

Ces tests couvrent les preuves, l’isolation des dossiers, la conservation de valeurs, les changements de page et de libellés. Ils ne constituent pas encore un test d’installation Chrome, de dépôt réel de PDF ou de compatibilité avec Indeed/APEC/Workday.
