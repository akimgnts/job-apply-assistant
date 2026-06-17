def get_letter_prompt(
    offer,
    positioning,
    gap_analysis,
    cv_payload,
) -> str:
    """Generate French cover letter prompt.

    Philosophy:
    - NOT autobiographical
    - NOT CV summary
    - FORWARD-LOOKING: what can Akim bring?
    - 5 paragraphs, ~20 lines total

    Structure:
    1. Opening: business challenge from offer
    2. Offer of service: skills → challenges
    3. Interview proposal

    Language: French
    Style: professional, clear, human
    """

    company = offer.get("company", "l'entreprise")
    job_title = offer.get("job_title", "le poste")
    missions = ", ".join(offer.get("missions", [])[:2])
    confidence = gap_analysis.get("confidence", 0.5)
    bridges = gap_analysis.get("bridges", [])

    return f"""LETTRE DE MOTIVATION V1

=== PHILOSOPHIE ===

Pas une biographie.
Pas un résumé du CV.
Une argumentation : "Pourquoi Akim fait sens pour ce rôle?"

Répondre à : "Que peut Akim apporter à cette mission?"
Pas à : "Pourquoi Akim a choisi ce parcours?"

=== STRUCTURE (5 paragraphes) ===

PARAGRAPHE 1: Analyse du contexte
- Identifier 1-2 enjeux métier majeurs de l'offre
- Montrer la compréhension du problème
- Pas de biographie personnelle

Exemples d'ouverture:
"Dans un environnement où X est une priorité..."
"L'enjeu de Y requiert une capacité à..."
"La transformation de Z constitue un défi stratégique..."

PARAGRAPHE 2-3: Offer of Service
- Connecter les compétences réelles d'Akim à ces enjeux
- Utiliser le CV comme preuve, pas comme résumé
- Tonalité action : "Ma maîtrise de... permet de..."

Exemples:
"Ma maîtrise de SQL, Python et Power BI me permet d'assurer..."
"Cette expérience en reporting me permet de contribuer à..."
"L'approche que j'ai développée en automatisation..."

PARAGRAPHE 4: Bridges (si applicable)
- Utiliser gap_analysis.bridges
- Montrer les connexions non-évidentes
- Honnête sur les écarts

PARAGRAPHE 5: Proposal de rencontre
- Proactif, pas demandeur
- Orienté métier

Exemple:
"Je souhaite vous rencontrer afin d'échanger sur vos besoins
et sur la manière dont mes compétences en analyse de données
pourraient contribuer au développement de vos projets."

=== RÈGLES DE STYLE ===

Langue: Français
Tonalité: Pro, clair, direct, humain

Éviter:
  ❌ "depuis toujours passionné"
  ❌ "mon parcours atypique"
  ❌ "j'ai appris à"
  ❌ "je suis motivé par"
  ❌ "ma passion pour"
  ❌ répéter le CV
  ❌ "expert en"
  ❌ "leader"
  ❌ "dirigé une équipe"
  ❌ clichés corporate
  ❌ "je souhaite intégrer une entreprise où"

Préférer:
  ✓ "La capacité à..."
  ✓ "L'enjeu consiste à..."
  ✓ "Ma maîtrise de..."
  ✓ "Cette approche permet de..."
  ✓ "Je souhaite vous rencontrer..."
  ✓ "Contribuer à..."
  ✓ "Accompagner..."

=== CONTEXT ===

Entreprise: {company}
Poste: {job_title}
Missions clés: {missions}

Positioning: {positioning}
Confidence: {confidence}
Bridges: {", ".join(bridges) if bridges else "none"}

=== GAP-AWARE WRITING ===

Confiance haute (0.75+):
  Écrire avec alignement direct

Confiance moyenne (0.50-0.74):
  Construire les ponts avec soin
  Pas de surenchère

Confiance faible (< 0.50):
  Honnêteté sur les écarts
  Seulement compétences transversales
  Pas de faux séniorité

=== VALIDATION ===

✓ Français
✓ 4-6 paragraphes
✓ ~15-20 lignes total
✓ Pas "None"
✓ Pas lignes de contact vides
✓ Pas termes de faux séniorité
✓ Pas "expert", "leader", "dirigé équipe"
✓ Pas "depuis toujours passionné"
✓ Paragraphes ≤ 6 lignes

=== RETURN ===

Return ONLY valid JSON:

{{
  "object": "Candidature — {job_title} — {company}",
  "paragraphs": [
    "Paragraph 1 (business challenge understanding)",
    "Paragraph 2 (offer of service 1)",
    "Paragraph 3 (offer of service 2)",
    "Paragraph 4 (bridges if applicable)",
    "Paragraph 5 (interview proposal)"
  ],
  "signature": "Akim Guentas"
}}

=== CRITICAL ===

- Never invent companies, tools, experience
- Never claim seniority not held
- Never write "led" or "managed" if not done
- If confidence < 0.50: be even more careful about claims
- Forward-looking, not backward-looking
- Business-focused, not personal-focused
"""
