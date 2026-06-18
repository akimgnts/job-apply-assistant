# HANDOFF — CV Impact Generation

**Date:** 2026-06-18
**Branch:** master
**Commits applied in this session:** see git log

---

## 1. État actuel du système

### Pipeline CV réel

```
GenerationAgent.generate_cv()
  → load_master_cv()              # master_cv_service.py — source de vérité hardcodée
  → GapAnalysisAgent.analyze_gap()
  → BridgeEngine.reason_fit()
  → CVAdaptationAgent.adapt_cv()  # appelle adaptation_prompt.py
  → validate_adaptation()
  → render_cv(template="master_cv.html")
  → save to DB + file
```

Le prompt `get_cv_payload_prompt` dans `generation_prompt.py` **n'est pas utilisé** dans ce pipeline. Il existe mais n'est pas appelé par `GenerationAgent.generate_cv()`.

### Fichiers clés

| Fichier | Rôle |
|---------|------|
| `app/services/master_cv_service.py` | Source de vérité — bullets hardcodés, faits immuables |
| `app/prompts/adaptation_prompt.py` | Prompt principal de génération des bullets adaptés |
| `app/agents/cv_adaptation_agent.py` | Agent qui appelle le prompt d'adaptation |
| `app/agents/generation_agent.py` | Orchestrateur — charge master CV, adapte, rend |
| `app/templates/master_cv.html` | Template HTML réellement utilisé |
| `app/prompts/generation_prompt.py` | Contient `get_cv_payload_prompt` — NON utilisé pour CV |

---

## 2. Problème observé

Le CV généré produisait des bullets génériques du type :

```
"Built KPI dashboards using Power BI."
"Supported data quality through structured reporting processes."
```

Causes identifiées :

### Cause 1 — `master_cv_service.py` : bullets source déjà génériques

Les bullets Sidel hardcodés ne contenaient aucun chiffre :
```python
# AVANT (générique)
"Structured and maintained reporting supports for marketing, communication and commercial teams using Excel, Power BI and Power Query.",
"Supported data quality through cleaning, consistency checks, documentation and structured reporting processes.",
```

Pourtant les données vérifiées existent : ~10 dashboards, ~30-40 utilisateurs, traitement manuel = demi-journée à plusieurs jours, 61 clients Wines & Spirits.

### Cause 2 — `adaptation_prompt.py` : liste `ALWAYS USE` contre-productive

Le prompt encourageait activement les verbes mous :
```
ALWAYS USE (preferred):
  • contributed to
  • helped deliver
  • involved in
  • participated in
  • worked on
  • supported
```

Ces formulations sont exactement les anti-patterns qui rendent un CV générique.

### Cause 3 — Absence de règle "evidence-first" dans le prompt

Le STEP 4 du prompt d'adaptation n'exigeait pas de justification chiffrée dans chaque bullet. Les exemples fournis étaient eux-mêmes génériques :
```
# Exemple dans le prompt AVANT
Prefer: "Consolidated and analyzed multi-source business data to improve visibility..."
```

---

## 3. Fichiers analysés

- `app/services/master_cv_service.py` — bullets sources
- `app/prompts/adaptation_prompt.py` — prompt principal de génération
- `app/prompts/generation_prompt.py` — prompt alternatif (non utilisé pour CV)
- `app/agents/generation_agent.py` — pipeline d'orchestration complet
- `app/agents/matching_agent.py` — sélection des blocs de profil
- `app/templates/master_cv.html` — template HTML actif
- `app/services/document_service.py` — rendu Jinja2
- `app/database/seed_profile.py` — blocs profil PostgreSQL (enrichis séparément)

---

## 4. Changements effectués

### `app/services/master_cv_service.py`

**Sidel — 7 bullets, tous enrichis avec données vérifiées :**

```python
# APRÈS
"Built and maintained around 10 dashboards and reporting tools covering installed base, events and business KPIs — used weekly and monthly by approximately 30–40 stakeholders across marketing, commercial and management teams.",
"Automated recurring extraction, cleaning, consolidation and visualization tasks using Python, SQL and Power BI — reducing processes that previously required half a day to several days of manual work.",
"Analyzed installed base, equipment and service data across 61 customers in the Wines & Spirits sector; produced commercial action plans supporting account prioritization by machine age, installed base evolution and business opportunities.",
"Consolidated multi-source business data (customers, leads, events, campaigns) and monitored KPIs to improve operational visibility for European marketing and commercial teams.",
"Coordinated with international stakeholders across Europe; presented analyses, action plans and business insights in French and English.",
"Supported data quality through structured cleaning, consistency checks and documentation across multi-source reporting processes.",
"Used Python, SQL, Snowflake, Power BI, Power Query and Microsoft Dynamics for data consolidation, reporting and business analysis in a large-scale B2B industrial context.",
```

**MadeByAkim — ajout de "saving several hours of manual work" :**
```python
"Automated repetitive operational tasks (email preparation, meeting workflows, lead enrichment) — saving several hours of manual work per workflow across systems used by clients and personal operations.",
```

**Elevia — 3 bullets avec chiffres vérifiés (anciennement 1 bullet générique) :**
```python
"Designed and iterated through more than 10 versions of a matching engine — evaluated across 30 test profiles and over 1,000 job opportunities, improving recommendation quality and explainability.",
"Generated 100+ AI-assisted application documents (CVs, cover letters, recruiter messages) — reducing preparation time from dozens of minutes to a few seconds.",
"Built a modular architecture of ~10 components across 4 PostgreSQL tables, covering CV parsing, skill extraction, canonicalization, scoring and observability.",
```

**Job Apply Assistant — ajout de la réduction de temps :**
```python
"Built a Telegram assistant that analyzes job offers, matches against a candidate profile and generates tailored CV, cover letter and recruiter message — reducing application preparation time from ~45 minutes to ~5 minutes.",
```

### `app/prompts/adaptation_prompt.py`

**Suppression de la liste `ALWAYS USE` (verbes mous).**

**Remplacement par :**
```
PREFER specific, grounded language:
  "Built and maintained 10 dashboards used by 30–40 stakeholders" (not "created reporting tools")
  "Automated tasks that previously required half a day to several days" (not "reduced manual effort")
```

**Ajout de la règle EVIDENCE-FIRST BULLET :**
```
Every bullet must contain at least one of:
  ✓ A concrete number (10 dashboards, 30–40 users, 61 customers, half a day saved)
  ✓ An operational before/after (previously X days → now Y hours)
  ✓ A specific stakeholder scope
  ✓ A measurable output (100+ documents, 1,000+ opportunities)
```

**Mise à jour des exemples few-shot dans STEP 4 :**
```
# Avant (générique, dans le prompt)
"Consolidated and analyzed multi-source business data to improve visibility on customer and market performance."

# Après (evidence-first, dans le prompt)
"Built and maintained around 10 dashboards covering installed base, events and KPIs — used weekly by ~30–40 stakeholders across marketing, commercial and management teams."
```

---

## 5. Règles de génération ajoutées

### Dans `adaptation_prompt.py`

```
EVIDENCE-FIRST BULLET RULE:
Every bullet must contain at least one of:
  ✓ A concrete number
  ✓ An operational before/after
  ✓ A specific stakeholder scope
  ✓ A measurable output

Never invent numbers. Never use vague percentages.
Never use "significantly" or "greatly".
```

```
FORBIDDEN (extended):
  contributed to / helped improve / participated in / involved in
  assisted with / supported the team / helped deliver
  passionate about / results-oriented / team player
```

---

## 6. Exemples avant / après

### Sidel — Reporting

| | Bullet |
|---|---|
| **AVANT** | "Structured and maintained reporting supports for marketing, communication and commercial teams using Excel, Power BI and Power Query." |
| **APRÈS** | "Built and maintained around 10 dashboards and reporting tools covering installed base, events and business KPIs — used weekly and monthly by approximately 30–40 stakeholders across marketing, commercial and management teams." |

### Sidel — Automation

| | Bullet |
|---|---|
| **AVANT** | "Supported data quality through cleaning, consistency checks, documentation and structured reporting processes." |
| **APRÈS** | "Automated recurring extraction, cleaning, consolidation and visualization tasks using Python, SQL and Power BI — reducing processes that previously required half a day to several days of manual work." |

### Elevia

| | Bullet |
|---|---|
| **AVANT** | "Personal project in development around CV parsing, skills extraction, canonicalization, scoring, matching, explainability, data quality, observability and AI-assisted document generation." |
| **APRÈS** | "Designed and iterated through more than 10 versions of a matching engine — evaluated across 30 test profiles and over 1,000 job opportunities, improving recommendation quality and explainability." |

### Job Apply Assistant

| | Bullet |
|---|---|
| **AVANT** | "Telegram assistant that analyzes job offers, compares them with a candidate profile, proposes positioning and generates adapted CV, letter and recruiter message." |
| **APRÈS** | "Built a Telegram assistant that analyzes job offers, matches against a candidate profile and generates tailored CV, cover letter and recruiter message — reducing application preparation time from ~45 minutes to ~5 minutes." |

---

## 7. Garde-fous anti-hallucination

### Existants (inchangés)
- `validate_adaptation()` dans `master_cv_service.py` rejette toute adaptation qui réordonne les expériences ou supprime des bullets Sidel (minimum 5 requis)
- Fallback `_build_fallback_adaptation()` si l'adaptation échoue la validation
- `ABSOLUTE RULES` dans le prompt : jamais de chiffres inventés, jamais de certifications fabricées

### Règle ajoutée
```
Never invent numbers. Never use vague percentages. Never use "significantly" or "greatly".
If no number is available in the source data, use truthful qualitative specificity.
```

### Données vérifiées disponibles dans `master_cv_service.py`

| Expérience | Données vérifiées |
|---|---|
| Sidel | ~10 dashboards, ~30-40 utilisateurs, demi-journée à plusieurs jours, 61 clients W&S |
| MadeByAkim | plusieurs heures économisées par workflow |
| Elevia | 10+ versions, 30 profils test, 1000+ offres, 100+ documents |
| Job Apply Assistant | ~45 min → ~5 min |

---

## 8. Prochaines étapes

### Court terme
- [ ] Redéployer via Coolify (re-seed DB avec nouveaux blocs + nouveau code)
- [ ] Tester sur une offre Data Analyst BI et vérifier que les bullets contiennent des chiffres
- [ ] Tester sur une offre Automation/Ops et vérifier que les bullets MadeByAkim sont spécifiques

### Moyen terme
- [ ] Ajouter des données vérifiées pour Vassard OMB (actuellement peu de chiffres)
- [ ] Envisager un champ `evidence_level: verified | estimated | qualitative` dans `master_cv_service.py` pour distinguer clairement les chiffres exacts des approximations
- [ ] Ajouter un test automatique qui valide que les bullets générés contiennent au moins un chiffre ou une donnée spécifique (pas de bullet entièrement générique)

### Architecture
- Clarifier le rôle de `generation_prompt.py` (`get_cv_payload_prompt`) — actuellement non utilisé pour le CV, à supprimer ou documenter explicitement
- Le pipeline réel passe par `adaptation_prompt.py` + `master_cv_service.py` → toute amélioration de la qualité de génération doit passer par ces deux fichiers

---

## Résumé des fichiers modifiés

| Fichier | Type de changement |
|---|---|
| `app/services/master_cv_service.py` | Sidel bullets enrichis (×7), MadeByAkim (×5), Elevia (1→3 bullets), Job Apply Assistant (ajout timing) |
| `app/prompts/adaptation_prompt.py` | ALWAYS USE supprimé, EVIDENCE-FIRST ajouté, exemples few-shot mis à jour |
| `app/database/seed_profile.py` | Enrichi avec impact knowledge base Sidel (4 zones) + dates + écoles + nouveaux outils |
| `app/prompts/generation_prompt.py` | WRITING STANDARD ajouté (non utilisé pour CV, mais utilisé si fallback) |
| `Dockerfile` | Playwright install non-fatal |
