# LOCKED ARCHITECTURE — FINAL
## 12 Corrections Applied. Verdict & Acceptance Criteria.

**Status**: Architecture locked. Ready for Phase 0/1 implementation start.

---

## A. CORRECTED PHASE ORDER

Phase dependency fixed: structured requirements must exist before Evidence Matrix builds.

```
PHASE 0 — Baseline + Real Fixtures
  Input: Bayestra / FullEnrich / FR offers (real)
  Output: frozen golden HTML, diagnostic outputs, known failures documented
  Invariants locked: structural, factual, numerical
  Test: comparison against baseline (not LLM-identical reproduction)
  ✓ GO/NO-GO gate before Phase 1

PHASE 1 — Master V3.1 Explicit Stable IDs
  Input: master_cv_v3.json (FR)
  Output: explicit evidence_id fields added to every bullet, project, skill
  Structure:
    - Experience IDs: EXP.SIDEL, EXP.MBA, EXP.VASSARD
    - Project IDs: PROJECT.ELEVIA, PROJECT.JOBAPPLY, PROJECT.NUITBLANCHE
    - Skill IDs: SKILL.PYTHON, SKILL.SQL, SKILL.POWERBI, SKILL.FASTAPI, SKILL.DOCKER, SKILL.POSTGRESQL, SKILL.COOLIFY
    - Bullet IDs: SIDEL.DATA.001, SIDEL.DATA.002, ..., MBA.BACKEND.001, ..., PROJECT.ELEVIA.AI.001, ...
  Rule: IDs are explicit persisted fields in JSON. Never computed from array index.
  Rule: ID must survive reordering, deletion, insertion of other bullets.
  Test: ID immutability (reorder → IDs unchanged)
  ✓ GO/NO-GO gate before Phase 2

PHASE 2 — AnalysisAgent OFFER-ONLY Refactor
  Input: raw job offer
  Output: structured requirements[] + job_environment + role_family (offer-only)
  Removes: profile_blocks, match_score, strengths, missing_points (all FUTURE outputs)
  New fields per requirement:
    - text: requirement description
    - category: "technology | capability | practice | mission | domain | soft"
    - importance: "MUST_HAVE | IMPORTANT | NICE_TO_HAVE"
    - origin: "EXPLICIT | INFERRED_CONTEXT"  ← Track source
    - confidence: 0.0-1.0
  Rule: INFERRED_CONTEXT may infer capability/practice from offer semantics.
         INFERRED_CONTEXT MUST NOT invent specific technology.
         If offer says "Python", origin=EXPLICIT. If offer says "data pipeline", Python is not inferred.
  Rule: job_environment contains only EXPLICIT offer details. Zero candidate pollution.
  Test: requirement origin tracking, INFERRED_CONTEXT does not hallucinate tech
  ✓ GO/NO-GO gate before Phase 3

PHASE 3 — EvidenceMatrixService
  Input: structured requirements[] + master_cv_v3.json
  Output: evidence_matrix_json
  Contracts:
    - Each requirement maps to 0..N evidence items from Master
    - Each evidence item contains: evidence_id (SIDEL.DATA.001) + relationship (DIRECT|SUPPORTING|DELIVERY) + match_level (STRONG|PARTIAL|WEAK) + reasoning
    - All evidence_ids must exist in Master V3.1 (Python validates)
    - Python computes deterministic match_score from requirement importance × requirement match_level across all requirements
  Match score formula (DETERMINISTIC, not LLM-generated):
    score = sum(req.importance_weight * coverage_for_req) / sum(req.importance_weight)
    where importance_weight = {MUST_HAVE: 1.0, IMPORTANT: 0.7, NICE_TO_HAVE: 0.3}
    and coverage_for_req = max(match_level across evidence) where STRONG=1.0, PARTIAL=0.5, WEAK=0.2, MISSING=0.0
  Outputs also: strengths[], gaps[] (derived from matrix)
  Rule: OpenAI returns ONLY known evidence_id + relationship + match_level + reasoning. No invented scores, no invented evidence_ids.
  Test: matrix structure, deterministic score calculation, requirement→evidence mapping accuracy
  ✓ GO/NO-GO gate before Phase 4

PHASE 4 — Persistence + integrate handle_offer
  Input: AnalysisAgent output + EvidenceMatrixService output
  Output: job_analyses record with full matrix (computed ONCE)
  Location: Move EvidenceMatrixService.build_matrix() call from generate_cv() to handle_offer()
  Result: score + strengths + gaps available at Telegram response time (not deferred to /GO)
  Test: matrix persisted, not recalculated at /GO
  ✓ GO/NO-GO gate before Phase 5

PHASE 5 — PositioningAgent Consumes Matrix
  Input: structured requirements + evidence_matrix_json + master_cv_v3 + VALID_ANGLES
  Output: positioning string (must be in VALID_ANGLES)
  Rule: Positioning frames the available evidence. Does not precede it.
  Rule: Do NOT allow free-form positioning string generation.
        VALID_ANGLES fixed list. Evidence Matrix helps choose which one applies best.
  Correct example: If evidence shows engineering (automation, APIs), select "Data & AI Consultant | Automation & Pipeline Architecture" from list.
  WRONG: "Data Scientist & ML Ops Engineer" — invents new positioning outside VALID_ANGLES.
  Test: selected positioning is in VALID_ANGLES, evidence justifies the choice
  ✓ GO/NO-GO gate before Phase 6

PHASE 6 — CVAdaptationAgentV3 Enhanced
  Input: job_environment + requirements + evidence_matrix_json + master_cv_v3 + positioning
  Output: selected_evidence_ids[] (array of evidence_id strings, NO REWRITING)
  Contract:
    OpenAI sees:
    - requirement text + importance + origin
    - for each requirement: current evidence matches (DIRECT/SUPPORTING/DELIVERY) + match_level
    - authorized evidence text (from master_cv_v3) + metadata (tags, skills, technologies)
    - positioning context
    
    OpenAI returns JSON:
    {
      "selected_evidence_ids": ["SIDEL.DATA.001", "SIDEL.DATA.003", "MBA.BACKEND.001", ...],
      "reasoning": "Bayestra requires automation + pipelines. Sidel has 6+ dashboards (PARTIAL), MBA has API+backend automation (STRONG).",
      "coverage": {"requirements_covered": 7, "requirements_partial": 2, "requirements_missing": 0}
    }
    
    Python validates:
    - All evidence_ids exist in Master
    - No rewriting/adaptation (text from Master is EXACT)
    - Reasoning is coherent
  Test: Bayestra selection ≠ FullEnrich selection (thematic differentiation)
  ✓ GO/NO-GO gate before Phase 7

PHASE 7 — Composition: Ordering, Marginal Value, No Quotas
  Input: selected_evidence_ids[]
  Outputs:
    - experience_order: dynamic by total evidence_strength (not hardcoded Sidel first)
    - project_order: dynamic by evidence coverage
    - skills_order: dynamic by evidence strength + requirement coverage
  Rules:
    - No percentage/count quotas (30-40% is observation, not rule)
    - Selection stops when: no new requirement coverage OR marginal_value ≤ threshold
    - If composition exceeds layout budget: remove evidence with lowest marginal_contribution_score
    - Layout budget is REAL (A4 pages); arbitrary character count is NOT a budget
  Test: marginal value logic, experience ordering changes per job, no hardcoded quotas
  ✓ GO/NO-GO gate before Phase 8

PHASE 8 — Safe Fallback (Deterministic)
  Input: if primary CVAdaptationAgentV3 selection fails OR evidence_ids validation fails
  Contract:
    Primary: semantic evidence-driven selection from CVAdaptationAgentV3
    Fallback: deterministic selection using persisted Evidence Matrix structure
      - Select all DIRECT evidence across all requirements
      - If still insufficient coverage, add SUPPORTING evidence
      - Compose in dynamic order by evidence strength
    Fail case: if deterministic selection produces no valid targeted CV → GENERATION FAILURE
  
  Rule: Fallback uses pre-computed Matrix (no new intelligence, no LLM retry)
        Never render the entire Master CV
        Never render an empty CV
        Never silently generate a generic/untargeted CV
  Test: fallback path produces valid targeted output OR fails cleanly with error
  ✓ GO/NO-GO gate before Phase 9

PHASE 9 — EN Sidecar Locked Translations
  Input: master_cv_v3.json (FR) + master_cv_v3_translations_en.json (locked EN)
  At CV generation time (cv_language = "en"):
    For each selected evidence_id:
      - Lookup in master_cv_v3_translations_en.json
      - If present → use it
      - If missing → GENERATION FAILURE (fail loud, not fallback to FR)
  Rule: NEVER fallback to French in an English CV.
        NEVER perform runtime LLM translation of facts.
  Rule: All sendable factual labels (skills, dates, company names) must have locked translations.
  Structure:
    {
      "SIDEL.DATA.001": "Designed and deployed 6+ dashboards...",
      "SIDEL.DATA.002": "Automated data pipeline, reducing processing time from 5–6 h to 1 h...",
      ...
    }
  Test: EN CV has no French text, missing translations cause fail (not silent skip)
  ✓ GO/NO-GO gate before Phase 10

PHASE 10 — QualityAgentV3 Pre/Post Validation
  Input: selected_evidence_ids[] + rendered_html (before save)
  Validation split:
    
    PRE-RENDER (before template rendering):
      - All evidence_ids exist in Master V3.1
      - No modified/altered metrics, dates, facts
      - Evidence belongs to authorized Master (no profile_blocks DB fallback)
    
    POST-RENDER (after Jinja2 template):
      - For cv_language="en": compare against sidecar translations EN
        (Do NOT compare to FR Master; template uses EN text via translations_en lookup)
      - For cv_language="fr": compare against FR Master
      - Verify expected evidence text present in HTML (normalize whitespace/entities)
      - Verify no fabricated claims (factually new text not in Master)
      - Verify no forbidden technologies
      - Verify no proficiency inflation
      - Verify no mixed-language prose (all factual statements in target language)
  
  Severity rules:
    
    REJECT (generation fails, no output):
    - unknown evidence_id
    - unauthorized factual text (invented fact)
    - metric/date altered
    - forbidden technology (e.g., Jira, Confluence, GCP, Looker Studio)
    - proficiency claim exceeds Master level
    - missing locked EN translation (cv_language="en")
    - residual mixed-language prose in facts
    - gap promoted into candidate capability claim
    
    REVIEW (output generated, but flagged for human review):
    - redundant evidence (same idea stated twice)
    - weak readability
    - unbalanced section emphasis
  
  Output:
    {
      "status": "SAFE | REVIEW | REJECT",
      "pre_render_issues": [...],
      "post_render_issues": [...],
      "quality_notes": "..."
    }
  
  Test: REJECT triggers on factual violations, REVIEW on quality concerns
  ✓ GO/NO-GO gate before Phase 11

PHASE 11 — E2E Integration Test
  Input: real offers (Bayestra, FullEnrich, FR)
  Full flow end-to-end:
    /offer → Analysis → Matrix → Positioning → Telegram response
    /GO → CVAdaptation → Composition → Render → Quality → HTML save → Telegram delivery
  
  Assertions:
    - Bayestra CV emphasizes engineering (automation, APIs, backend)
    - FullEnrich CV emphasizes analytics (dashboards, BI, data analysis)
    - FR CV has all text in French, EN CV has all text in English
    - No invented facts, no forbidden tech, no proficiency inflation
    - Quality status SAFE or REVIEW (no REJECT)
  
  Test: full pipeline works, outputs are correct, thematic differentiation confirmed
  ✓ RELEASE READY
```

---

## B. CORRECTED CANONICAL CALL GRAPH

```
TELEGRAM: /offer {raw_input}
  ↓
  InputAgent.process(raw_input)
    └─ return: (url | text_segment)
  ↓
  AnalysisAgent.analyze(job_offer)  // OFFER-ONLY, no profile_blocks
    └─ return: {
         job_title, company, missions,
         requirements: [{text, category, importance, origin, confidence}],
         job_environment: {core_capabilities, technical_stack, data_practices, ...},
         role_family: "engineering | analytics | bi | business_analyst | product"
       }
  ↓
  EvidenceMatrixService.build_matrix(analysis, master_cv)
    └─ return: {
         requirement_evidence_map: {req_id → [{evidence_id, relationship, match_level, reasoning}]},
         strengths: [...],
         gaps: [...],
         match_score: 0-100 (deterministic),
         evidence_clusters: {...}
       }
  ↓
  Save job_analyses(analysis + matrix)
  ↓
  PositioningAgent.choose_angle(analysis, matrix, master_cv)
    └─ return: positioning_string (from VALID_ANGLES)
  ↓
  UPDATE applications + job_analyses with positioning
  ↓
  Send Telegram: "Analysis complete. Score: {score}. Strengths: {strengths}. Gaps: {gaps}. Click /GO to generate CV."

───────────────────────────────────

TELEGRAM: /GO {application_id}
  ↓
  Load job_analyses (evidence_matrix already computed)
  ↓
  CVAdaptationAgentV3.adapt_cv(analysis, matrix, positioning, master_cv)
    └─ return: {
         selected_evidence_ids: ["SIDEL.DATA.001", ...],
         reasoning: "...",
         coverage: {...}
       }
  ↓
  CompositionService.order_and_structure(selected_evidence_ids, master_cv)
    └─ return: {
         experience_order: [0, 1, 2],
         project_order: [0, 1, 2],
         skills_order: [0, 1, 2, ...],
         experience_bullets: {0: [ids], 1: [ids], ...},
         project_bullets: {...},
         selected_skills: [...]
       }
  ↓
  Jinja2.render_cv(composition, master_cv, cv_language, translations_sidecar)
    └─ for each evidence_id:
         text = translations_sidecar.get(evidence_id) if cv_language=="en" else master_cv.get(evidence_id)
         if text is None and cv_language=="en": FAIL "Missing EN translation"
       └─ return: rendered_html_with_data_evidence_id_attrs
  ↓
  QualityAgentV3.validate_cv(selected_evidence_ids, master_cv, rendered_html, cv_language)
    └─ return: {status: "SAFE | REVIEW | REJECT", issues: [...]}
  ↓
  if status == "REJECT":
    Send Telegram: "CV generation failed: {issues}. Contact support."
    return
  ↓
  DocumentService.save_cv(html, application_id, cv_language, selected_evidence_ids, master_version)
  ↓
  Send Telegram: CV HTML + quality note
```

---

## C. FINAL DATA CONTRACTS

### Requirement Structure (AnalysisAgent output)
```json
{
  "requirement": {
    "id": "REQ_BAYESTRA_PYTHON",
    "text": "Python for data processing and API development",
    "category": "technology | capability | practice | mission | domain | soft",
    "importance": "MUST_HAVE | IMPORTANT | NICE_TO_HAVE",
    "origin": "EXPLICIT | INFERRED_CONTEXT",
    "confidence": 0.95
  }
}
```

**Rule**: `origin=EXPLICIT` only if requirement text appears in offer.
**Rule**: `origin=INFERRED_CONTEXT` may infer capability/practice, NEVER specific technology not in offer.

### Evidence Structure (Master V3.1)
```json
{
  "experience": {
    "id": 0,
    "evidence_id": "EXP.SIDEL",
    "title": "<AUTHORIZED_MASTER_TEXT>",
    "company": "<AUTHORIZED_MASTER_TEXT>",
    "dates": "<AUTHORIZED_MASTER_TEXT>",
    "bullets": [
      {
        "text": "<AUTHORIZED_MASTER_TEXT>",
        "evidence_id": "SIDEL.DATA.001",
        "tags": ["<FROM_MASTER>"],
        "technologies": ["<FROM_MASTER>"]
      },
      {
        "text": "<AUTHORIZED_MASTER_TEXT>",
        "evidence_id": "SIDEL.DATA.002",
        "tags": ["<FROM_MASTER>"],
        "technologies": ["<FROM_MASTER>"]
      }
    ]
  },
  "project": {
    "id": 0,
    "evidence_id": "PROJECT.ELEVIA",
    "title": "<AUTHORIZED_MASTER_TEXT>",
    "bullets": [
      {
        "text": "<AUTHORIZED_MASTER_TEXT>",
        "evidence_id": "ELEVIA.AI.001",
        "technologies": ["<FROM_MASTER>"]
      }
    ]
  },
  "skill": {
    "label": "<AUTHORIZED_MASTER_TEXT>",
    "evidence_id": "SKILL.PYTHON",
    "level": 3,
    "category": "<FROM_MASTER>"
  }
}
```

**Note**: All text values retrieved from authorized Master V3.1 JSON. No illustrative/invented candidate facts.
No dates, roles, job titles, or technologies are included here unless they appear in the locked Master source.

### Evidence Matrix (EvidenceMatrixService output, persisted in job_analyses)
```json
{
  "evidence_matrix_json": {
    "master_version": "3.1_locked_2026-08-28",
    "requirement_evidence_map": {
      "REQ_<JOB_ID>_<REQUIREMENT>": [
        {
          "evidence_id": "<EVIDENCE_ID_FROM_MASTER>",
          "experience_id": 0,
          "relationship": "DIRECT | SUPPORTING | DELIVERY",
          "match_level": "STRONG | PARTIAL | WEAK",
          "reasoning": "<EVIDENCE_JUSTIFICATION>"
        }
      ]
    },
    "strengths": [
      "<REQUIREMENT>: <MATCH_LEVEL> (<EVIDENCE_COUNT> evidence items)"
    ],
    "gaps": [
      "<REQUIREMENT>: MISSING (not in Master)"
    ],
    "match_score": 0-100,
    "match_score_formula": "sum(req.importance_weight * max(match_level)) / sum(req.importance_weight) × 100"
  }
}
```

**Note**: All evidence_ids must exist in Master V3.1. Match score deterministically calculated from requirement importance × evidence match levels. No invented requirements or evidence.

### CVAdaptationAgentV3 Output (selected_evidence_ids only)
```json
{
  "selected_evidence_ids": [
    "SIDEL.DATA.001",
    "SIDEL.DATA.002",
    "MBA.BACKEND.001",
    "PROJECT.ELEVIA.AI.001",
    "SKILL.PYTHON",
    "SKILL.SQL"
  ],
  "reasoning": "Bayestra engineering focus: selected automation + backend + core languages",
  "coverage": {
    "requirements_covered_strong": 4,
    "requirements_covered_partial": 3,
    "requirements_missing": 2
  }
}
```

---

## D. DETERMINISTIC MATCH-SCORE DESIGN

**Formula**:
```
score = sum(req_i.importance_weight × match_level_i) / sum(req_i.importance_weight) × 100

where:
  req_i.importance_weight = 
    MUST_HAVE: 1.0
    IMPORTANT: 0.7
    NICE_TO_HAVE: 0.3
  
  match_level_i = max([match_level of all evidence mapped to req_i])
    STRONG: 1.0
    PARTIAL: 0.5
    WEAK: 0.2
    MISSING: 0.0
```

**Example**:
```
Requirements:
  [1] Python (MUST_HAVE) → evidence SIDEL.DATA.002 (STRONG) → 1.0 × 1.0 = 1.0
  [2] Dashboards (IMPORTANT) → evidence SIDEL.DATA.001 (PARTIAL) → 0.7 × 0.5 = 0.35
  [3] Kubernetes (NICE_TO_HAVE) → MISSING → 0.3 × 0.0 = 0.0
  [4] Cloud (IMPORTANT) → evidence SIDEL.DATA.003 (WEAK) → 0.7 × 0.2 = 0.14

Score = (1.0 + 0.35 + 0.0 + 0.14) / (1.0 + 0.7 + 0.3 + 0.7) × 100
       = 1.49 / 2.7 × 100
       ≈ 55
```

**Determinism guarantee**: Given same requirements + same evidence_matrix, score is always identical. No LLM involvement in score calculation.

**Who computes**: Python code in EvidenceMatrixService, not OpenAI.

---

## E. FINAL DB OWNERSHIP

### Add to `job_analyses`:
```python
evidence_matrix_json: JSON  # Full matrix (requirement→evidence map, strengths, gaps)
match_version: str          # "3.1_locked_2026-08-28"
```

### Update `applications`:
```python
# match_score already exists; now populated from deterministic Evidence Matrix
# (was previously: direct LLM output or placeholder)
```

### Keep in `generated_documents` (existing):
```python
content: TEXT           # Rendered HTML (persisted for historical audit + download)
```

### Add to `generated_documents`:
```python
selected_evidence_ids: JSON     # ["SIDEL.DATA.001", "SIDEL.DATA.002", ...]
selection_reasoning_json: JSON  # {reasoning: "...", coverage: {...}}
master_version: str             # "3.1_locked_2026-08-28"
cv_language: str                # "fr" | "en"
generation_version: str         # "v3" (for future versioning)
quality_result_json: JSON       # {status: "SAFE|REVIEW|REJECT", issues: [...]}
```

**DO NOT store in matrix/matrix rows**: duplicate factual text (store IDs only, fetch text at render time from Master/sidecar).

**All factual retrieval at render time**: evidence_id → Master V3.1 JSON lookup (or sidecar translations_en if cv_language="en").

**Backward compatibility**: existing generated_documents.content field remains for historical audit trail.

---

## F. FINAL FAILURE/QUALITY RULES

Quality validation separates two distinct surfaces:

### FACTUAL_EVIDENCE_SURFACE
Candidate facts, accomplishments, metrics, dates, proficiency levels.
**Authorization**: Must come from Master V3.1 or sidecar translations (evidence_ids only).

**REJECT triggers**:
- Unknown evidence_id (does not exist in Master V3.1)
- Unauthorized factual text (sentence/claim not in Master)
- Metric/date altered (6+ becomes 5, 5–6 h becomes 8 h)
- Proficiency claim exceeds Master level (level 2 skill claimed as level 3)
- Forbidden technology used (Jira, Confluence, GCP, Looker Studio, etc.)
- Gap promoted into capability (missing skill claimed as present)
- Missing locked EN translation for cv_language="en"

### PRESENTATION_SURFACE
Non-factual layout/format: CV headlines, section headings, labels, contact formatting, positioning labels, safe summary framing.
**Authorization**: Deterministic templates, allowlists, verified evidence composition.
**Constraint**: Must not introduce new candidate facts.

**Examples of PRESENTATION valid elements** (do NOT require literal Master bullet identity):
- "Data & Business Analyst | BI · SQL · Data Quality" (framing of selected evidence)
- "akim guentas | Paris, France | akim.guentas@example.com" (contact, deterministic)
- Section heading: "Professional Experience" (template)
- Positioning label from VALID_ANGLES (verified allowlist)

**These DO NOT need literal Master text match; they need deterministic generation and factual consistency.**

### Validation by Surface

**FACTUAL_EVIDENCE_SURFACE validation**:
- All evidence_ids must exist in Master V3.1
- All evidence text must match Master (or sidecar EN if cv_language="en")
- No proficiency inflation, no metric alteration, no forbidden tech
- No mixed-language prose in facts

**PRESENTATION_SURFACE validation**:
- All values from deterministic templates, allowlists, or verified composition
- No new candidate facts introduced
- Language consistency (all presentation text in target cv_language)

### Quality Gate Outcomes

**REJECT (generation fails, user sees error)** — applies to FACTUAL_EVIDENCE_SURFACE violations:
- Unknown evidence_id
- Unauthorized factual text
- Metric/date altered
- Proficiency inflation
- Forbidden technology
- Gap promoted into capability
- Missing EN translation

**REVIEW (output generated, flagged)** — applies to presentation/redundancy concerns:
- Redundant evidence (same skill/achievement repeated in facts)
- Weak readability (awkward phrasing in presentation)
- Unbalanced emphasis (one experience dominates)

**SAFE (release as-is)**:
- All FACTUAL_EVIDENCE surface authorized
- All PRESENTATION surface deterministically generated
- No redundancy, good balance
- Language consistency confirmed

**User sees**:
- REJECT: "CV generation failed: {specific issue}. Please contact support."
- REVIEW: CV generated + "Note: Quality review suggested. Please check for [issue]."
- SAFE: CV generated, clean release.
- All text from Master
- Pre- and post-render validation passed
- No redundancy, balance acceptable
- Language consistency confirmed (cv_language matches all text)

**User sees**: CV generated, clean release.

---

## G. PHASE 0 ACCEPTANCE CRITERIA

**Goal**: Freeze baseline before code changes. Establish invariants.

**Inputs**:
- Bayestra offer (real production offer)
- FullEnrich offer (real production offer)
- FR offer (real production offer)

**Outputs to freeze**:
1. **Current Golden HTMLs**: Capture current app output for each offer (before changes).
2. **Diagnostic outputs**: current analysis_json, current positioning_json, current generated_documents
3. **Known failures**: Document any current bugs (e.g., empty CVs from positioning=None fix)
4. **Factual Invariants locked** (from authoritative Master V3.1):
   - Sidel has 6+ dashboards metric
   - Sidel has 5–6 h → ~1 h automation metric
   - Sidel has ~80% time reduction metric
   - Sidel has 61 accounts metric
   - Elevia has 10+ cycles metric
   - Elevia has 30 profiles metric
   - Elevia has 1 000+ offers metric
   - Job Apply has ~45 min → ~5 min time reduction metric
   - Skill levels: Python/SQL/Power BI/PostgreSQL/FastAPI/Docker/Coolify all level 3
   - Excluded tools (NOT present in candidate Master): Jira, Confluence, GCP, Looker Studio

**Tests**:
- load_master_cv() succeeds, validation passes
- Master facts are intact (metrics, dates, numbers match frozen source)
- No new failures vs current baseline

**Acceptance**:
- Golden HTML baseline saved
- Invariants documented
- Current behavior snapshot recorded
- ✅ GO to Phase 1

---

## H. PHASE 1 ACCEPTANCE CRITERIA

**Goal**: Master V3.1 with explicit stable evidence_ids is complete and validated.

**Deliverables**:
1. master_cv_v3.json updated with `evidence_id` fields on every bullet, project, skill
   - Format: EXP.SIDEL, SIDEL.DATA.001, SKILL.PYTHON, PROJECT.ELEVIA, etc.
   - JSON schema extended, structure immutable
2. load_master_cv() reads and validates evidence_ids exist (no duplicates, all well-formed)
3. Evidence ID registry document: complete list of all IDs and their sources

**Tests**:
- Evidence ID immutability: reorder bullets → IDs unchanged
- Evidence ID uniqueness: no duplicates
- Evidence ID existence: all referenced IDs in json are present
- load_master_cv() parses and validates structure

**Code coverage**:
- master_cv_service.py updated to parse evidence_ids
- Validation checks evidence_id presence and uniqueness

**Acceptance**:
- master_cv_v3.json locked with explicit IDs
- All golden tests pass (Bayestra/FullEnrich/FR still produce same output as Phase 0)
- Evidence matrix can be simulated manually (requirements → evidence_ids)
- ✅ GO to Phase 2

---

## I. FILES TOUCHED BY PHASE 0/1

**Phase 0** (read-only, diagnostics only):
- app/data/master_cv_v3.json — inspect structure
- app/agents/analysis_agent.py — understand current output
- app/agents/cv_adaptation_agent_v3.py — understand current selection
- app/services/master_cv_service.py — understand validation

**Phase 1** (modifications):
- `app/data/master_cv_v3.json` — ADD explicit evidence_id fields
- `app/services/master_cv_service.py` — UPDATE to validate evidence_ids (uniqueness, format)
- `tests/phase_1_test.py` — NEW tests for ID immutability + uniqueness
- `docs/EVIDENCE_ID_REGISTRY.md` — NEW document mapping all IDs

**Database migrations**: None required in Phase 0/1 (schema changes come Phase 4+).

**No changes to**:
- app/bot/handlers.py
- app/agents/analysis_agent.py
- app/agents/cv_adaptation_agent_v3.py
- Telegram interface

---

## J. GO/NO-GO FOR STARTING PHASE 0

**VERDICT: MAJOR_REWRITE_REQUIRED = NO**
**VERDICT: CORE_ARCHITECTURAL_REFACTOR_REQUIRED = YES**

**Reasoning**:
- Application structure remains intact (Telegram → agents → services → DB)
- Database schema changes are additive (no deletions)
- Public APIs (handlers, agents) remain compatible through refactoring
- Core refactoring occurs in intelligence layer only (analysis → matrix → selection → composition)

**Go/No-Go Checklist**:
- ✅ Phase order dependencies resolved
- ✅ Stable evidence IDs designed (explicit, not computed)
- ✅ Evidence Matrix contract defined (deterministic, no invented scores)
- ✅ AnalysisAgent scope narrowed (offer-only)
- ✅ Bilingual strategy locked (sidecar EN, no FR fallback)
- ✅ Quality rules clarified (REJECT vs REVIEW)
- ✅ Composition without quotas
- ✅ Phase 0/1 acceptance criteria locked
- ✅ Files to modify identified

**GO FOR PHASE 0/1**.

Start with Phase 0 baseline capture. Do NOT code Phase 1 logic changes until Phase 0 baseline is frozen and approved.

---

**Lock Confirmed**: Architecture is locked for implementation.
**Status**: Ready to proceed with Phase 0 baseline + Phase 1 Master V3.1.
