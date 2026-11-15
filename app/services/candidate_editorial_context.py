"""Reviewed editorial preferences; never a substitute for factual CV evidence."""

PREFERENCES = [
    {'id': 'evidence', 'label': 'Chaque affirmation doit être appuyée par le Master CV.',
     'rule': 'Relier les exigences aux preuves du Master CV. Ne jamais inventer de chiffres, de responsabilités ou de niveaux techniques.'},
    {'id': 'positioning', 'label': 'Un positionnement adapté et défendable.',
     'rule': 'Reformuler et hiérarchiser les preuves pour le poste. Ne pas adopter un titre Lead ou expert sans preuve. Mettre les preuves décisives dans le premier tiers.'},
    {'id': 'commitment', 'label': 'Mettre en avant les projets et l’engagement dans le poste.',
     'rule': 'Préférence exprimée les 10 et 27 octobre 2026 : valoriser les projets MadeByAkim et le portfolio sans suggérer un manque de disponibilité. Conserver le statut réel des missions freelance et ne jamais les transformer en emploi salarié.'},
    {'id': 'voice', 'label': 'Des messages naturels, précis et personnalisés.',
     'rule': 'Écrire simplement, avec un lien concret entre le besoin et une preuve. Éviter flatterie, enthousiasme générique, promesses et répétition du CV. Ne pas annoncer une pièce jointe ou un envoi sans confirmation du workflow.'},
    {'id': 'exploration', 'label': 'Les questions de salaire ne sont pas des exigences.',
     'rule': 'Ne pas déduire un minimum salarial ou un contrat exigé d’une question exploratoire. Ne pas inventer de préférence géographique ou contractuelle.'},
]


def editorial_context() -> str:
    return '\n'.join(['Préférences de rédaction validées, subordonnées aux faits du Master CV :'] +
                     [item['rule'] for item in PREFERENCES])
