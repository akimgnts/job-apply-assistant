# Reconciliation: Akim ChatGPT Assistant ↔ job-apply-assistant Architecture

**Date**: 2026-08-31  
**Status**: Research-only, no implementation  
**Purpose**: Extract complementary ideas without redesigning locked Phase 0/1 architecture

---

## 1. USEFUL_IDEAS_TO_KEEP

### 1.1 Direct Offer → Document Workflow
**From Akim system**: Job offer → silent analysis → CV delivery (no intermediate screens)  
**Current implementation**: `/offer` → analysis → save → Telegram response + `/GO` → CV  
**Assessment**: ✅ PARTIALLY ALIGNED  
- Akim's single-step CV generation (offer → CV immediate)
- Ours: two-step (offer → analysis first, then /GO → CV) for user agency
- No conflict: UX design choice, not architectural

### 1.2 Master = Factual Authority
**From Akim system**: Master CV is single source of truth; no invented facts  
**Current implementation**: Master V3.1 JSON with explicit evidence_ids  
**Assessment**: ✅ FULLY ALIGNED  
- Principle preserved: Master is factual authority
- Our implementation: more structured (JSON + evidence_ids vs HTML)
- No change needed

### 1.3 Template-Driven Structure
**From Akim system**: Visual structure fixed by template (`TEMPLATE_CV_CIBLE_AKIM.html`)  
**Current implementation**: Jinja2 templates (`app/templates/cv.html`, `letter.html`)  
**Assessment**: ✅ ALIGNED BUT DIFFERENT MECHANISM  
- Akim: manual `{{PLACEHOLDER}}` replacement
- Ours: Jinja2 context dict rendering
- Jinja is superior (DRY, reusable, logic-capable)
- Keep existing Jinja approach

### 1.4 Quality Verification Checklist
**From Akim system**: Final HTML verified against checklist before delivery  
**Current implementation**: QualityAgent, QualityAgentV2 exist  
**Assessment**: ✅ PARTIALLY PRESENT  
- Checklist items: authorization, no invention, A4 readability, no empty second page
- Our QualityAgentV2: factual validation exists
- Missing: explicit A4 visual validation

### 1.5 Silent Analysis Pattern
**From Akim system**: Analyze without showing reasoning, deliver result  
**Current implementation**: AnalysisAgent output used silently, Matrix built silently  
**Assessment**: ✅ ALIGNED  
- Our Evidence Matrix follows same pattern
- Telegram shows results, not analysis process

### 1.6 A4 Print Format Rules
**From Akim system**: Strict A4 dimensions, margins, page-break protection  
**Current implementation**: CSS with `@page { size: A4 }`, `page-break-inside: avoid`  
**Assessment**: ✅ ALIGNED  
- Our cv.html template includes A4 rules
- Typography, margins match Akim's approach

### 1.7 No Keyword Stuffing
**From Akim system**: Keywords appear naturally, supported by Master facts  
**Current implementation**: Evidence Matrix scores relevance  
**Assessment**: ✅ ALIGNED  
- Matrix prevents keyword injection without evidence
- Evidence must exist in Master

### 1.8 Language Distinction
**From Akim system**: Offer language determines CV language  
**Current implementation**: cv_language parameter + sidecar translation support  
**Assessment**: ✅ ALIGNED  
- No change needed

---

## 2. ALREADY_PRESENT_IN_CURRENT_ARCHITECTURE

| Feature | Component | Status |
|---------|-----------|--------|
| Letter generation | `LetterAgent` | ✅ EXISTS |
| Document rendering | `document_service` with Jinja | ✅ EXISTS |
| Multiple doc types | `GenerationAgent.generate_documents()` | ✅ EXISTS |
| CV template | `app/templates/cv.html` | ✅ EXISTS |
| Letter template | `app/templates/letter.html` | ✅ EXISTS |
| Quality validation | `QualityAgent`, `QualityAgentV2` | ✅ EXISTS |
| Master loading | `master_cv_service.load_master_cv()` | ✅ EXISTS |
| A4 print CSS | CV template | ✅ EXISTS |
| Silent analysis | Analysis + Matrix computation | ✅ EXISTS |
| Language detection | `language_service` | ✅ EXISTS |
| Master as authority | Locked principle | ✅ LOCKED |
| Template structure | Jinja2 rendering | ✅ EXISTS |

---

## 3. EXISTING_COMPONENTS_TO_EXTEND

### 3.1 LetterAgent → APEC Formalization
**Current state**: `LetterAgent.generate_letter_payload()` exists  
**What Akim adds**: APEC structure (two major challenges → evidence → projection → proposal)  
**Recommendation**: 
- ✅ EXTEND existing LetterAgent
- Add APEC-specific prompt structure to `letter_prompt.py`
- Formalize: identify two challenges → map to Evidence Matrix → select 2-3 pieces of evidence → projection
- Keep existing LetterAgent method signature

**Phase**: Post-Phase 11 (after CV architecture stable)

### 3.2 QualityAgentV2 → Surface-Specific Validation
**Current state**: `QualityAgentV2.validate_document()` exists  
**What Akim adds**: Distinction between FACTUAL_EVIDENCE_SURFACE (strict Master auth) + PRESENTATION_SURFACE (template-based, no new facts)  
**Recommendation**:
- ✅ EXTEND existing QualityAgentV2
- Add surface-aware validation (already designed in locked architecture)
- Keep existing component name/location

**Phase**: Phase 10 (QualityAgentV3 formalization)

### 3.3 CV Template → Minor Visual Enhancements
**Current state**: `app/templates/cv.html` implements A4 rules  
**What Akim adds**: Specific typography/hierarchy best practices (one-column, clear skills blocks, experience order)  
**Recommendation**:
- Compare `app/templates/cv.html` against `TEMPLATE_CV_CIBLE_AKIM.html`
- Extract specific improvements (if any) that don't conflict
- Do NOT replace entire template
- Do NOT add sidebars or multi-column layouts

**Phase**: Post-release refinement (not Phase 0/1)

### 3.4 Handlers.py → UX Pattern Alignment
**Current state**: `/offer` → analysis → `/GO` → document generation  
**What Akim adds**: Automatic CV trigger without user confirmation  
**Recommendation**:
- UX is already compatible
- No code changes needed
- Principle preserved: silent analysis, direct delivery

---

## 4. IDEAS_TO_REJECT

| Idea | Reason | Status |
|------|--------|--------|
| HTML Master as runtime source | We use JSON Master V3.1; HTML is reference only | ❌ REJECT |
| Manual `{{PLACEHOLDER}}` replacement | Jinja2 is superior | ❌ REJECT |
| Second factual source | Violates single source of truth | ❌ REJECT |
| Implicit "select relevant" logic | Evidence Matrix makes selection explicit | ❌ REJECT |
| Duplicate Master (FR + EN files) | Use sidecar translations file | ❌ REJECT |
| Free-form positioning | Use authorized VALID_ANGLES list | ❌ REJECT |
| Percentage-based content quotas | Use marginal_evidence_value | ❌ REJECT |
| Runtime LLM translation of facts | Use locked translation sidecar | ❌ REJECT |

---

## 5. PHASE_MAPPING

| Useful Idea | Belongs to Phase | Reason |
|-------------|------------------|--------|
| Master as authority | Phase 0/1 | Already locked |
| Template structure | Phase 0/1 | Already locked |
| Silent analysis | Phase 0/1 | Already locked |
| Evidence Matrix | Phase 0-4 | Already locked |
| QualityAgentV2 → QualityAgentV3 surfaces | Phase 10 | Quality validation split |
| LetterAgent → APEC formalization | Phase 12+ | Post-CV release |
| A4 visual validation | Phase 10 or later | Layout checks |
| Data-evidence-id attributes | Phase 10 | Audit trail |

---

## 6. LETTER_PIPELINE_REUSE_PLAN

**Current state**: LetterAgent exists with basic generation  
**Akim's APEC method**: 

```
Two major job challenges
    ↓ (identified silently)
Evidence Matrix (persisted from /offer)
    ↓ (proof selection from Matrix)
2–3 verified evidence items
    ↓
forward-looking service proposition
    ↓
proactive interview proposal
    ↓
render through template
```

**How to integrate**:

1. **Do NOT create LetterGenerationAgent**  
   - Extend existing `LetterAgent.generate_letter_payload()`

2. **Extend letter_prompt.py**  
   ```python
   def get_letter_prompt_apec(
       offer: dict,                    # two challenges identifiable here
       evidence_matrix: dict,          # strengths/gaps already identify challenges
       positioning: str,               # framing
       selected_evidence: list[str]    # 2-3 evidence_ids from Matrix
   ) -> str:
       # Prompt structure:
       # 1. Identify two major challenges from offer
       # 2. For each challenge, show evidence_matrix strengths/gaps
       # 3. Select 2-3 strongest evidence items
       # 4. Formulate service proposition (not autobiographical)
       # 5. Propose interview
   ```

3. **Keep existing LetterAgent method signature**  
   ```python
   async def generate_letter_payload(
       offer: dict,
       positioning: str,
       gap_analysis: dict,    # this is our Evidence Matrix equivalent
       cv_payload: dict = None
   ) -> dict
   ```
   - Input `gap_analysis` = Evidence Matrix strengths/gaps
   - Method already has right inputs

4. **Add APEC-specific validation to LetterAgent._validate_letter()**  
   - Check: ~20 lines (4 paragraphs)
   - Check: two challenges identified in first paragraph
   - Check: no chronological career narrative
   - Check: no raw CV repetition
   - Check: present-tense projection dominant
   - Check: no generic company flattery

**Phase**: 12+ (after CV architecture stabilized)

---

## 7. QUALITY_RULES_TO_REUSE

### From Akim Checklist:

```
✅ Every factual claim is authorized by Master
✅ Important verified requirements represented
✅ No invented content
✅ No exaggerated claims
✅ No repeated/redundant elements
✅ No placeholders remaining
✅ Valid, printable HTML
✅ No broken sections
✅ Correct target language
✅ A4 readable
✅ No nearly-empty second page
✅ Clear positioning visible in first third
✅ Skill levels remain honest
```

### Mapping to QualityAgentV3:

**FACTUAL_EVIDENCE_SURFACE** (strict):
```
✓ Every evidence_id exists in Master V3.1
✓ Evidence text matches Master (or sidecar EN if cv_language="en")
✓ No fabricated claims
✓ Metrics/dates not altered
✓ Proficiency not inflated
✓ No forbidden technologies
✓ No gaps promoted as capabilities
✓ Correct language for target cv_language
```

**PRESENTATION_SURFACE** (template-based):
```
✓ Headline/positioning clear in first third
✓ Section headings deterministic from template
✓ Contact info properly formatted
✓ No nearly-empty second page
✓ Typography readable on A4
✓ No orphaned headings or sections
```

**Keep existing**:
- QualityAgentV2 factual validation
- Extend with surface-aware logic (already designed)
- Add layout/visual rules

---

## 8. TEMPLATE_RULES_TO_REUSE

### From Akim's TEMPLATE_CV_CIBLE_AKIM.html:

```
✓ One-column linear layout (ATS-compatible)
✓ Clear typographic hierarchy
✓ A4 print dimensions (210mm × 297mm)
✓ Specific margins (10mm/12mm per side)
✓ Arial/sans-serif typography
✓ Page-break protection on sections
✓ Skills displayed as label + value pairs
✓ Experience: title, company, dates in row
✓ Bullet points for achievements
✓ Projects in subtle boxes (light background)
✓ Education section at end
✓ Contact info compact in header
✓ No visual decorations (icons, sidebars, gauges)
✓ ATS-readable: plain text labels
```

### Comparison with `app/templates/cv.html`:

- ✅ One-column: YES
- ✅ A4 format: YES
- ✅ Page-break rules: YES
- ✅ Clear hierarchy: YES
- ✅ No sidebars: YES
- ✅ ATS-compatible: YES
- ⚠️ Typography: Manrope (current) vs Arial (Akim) — no change needed (both readable)
- ⚠️ Project styling: subtle background (current) vs light box (Akim) — already similar

**Recommendation**: Current template already incorporates these principles.  
**Action**: No changes needed for Phase 0/1.

---

## 9. THINGS_THAT_MUST_NOT_CHANGE

### Critical Locks (From LOCKED_ARCHITECTURE_FINAL.md):

| Component | Lock Status | Reason |
|-----------|-------------|--------|
| Master V3.1 JSON source | 🔒 LOCKED | Single factual authority |
| Evidence_ids (explicit, not computed) | 🔒 LOCKED | Immutable identity |
| Evidence Matrix at analyze-time | 🔒 LOCKED | Build once, reuse always |
| Deterministic score formula | 🔒 LOCKED | No LLM-generated scores |
| No percentage/quota caps | 🔒 LOCKED | Evidence-driven, not quota-driven |
| Jinja2 templating | 🔒 LOCKED | Superior to placeholder replacement |
| Sidecar translations (EN) | 🔒 LOCKED | No runtime LLM translation |
| QualityAgentV3 two-surface validation | 🔒 LOCKED | Factual + presentation split |
| VALID_ANGLES positioning only | 🔒 LOCKED | No free-form positioning |
| Phase 0/1 scope (Master IDs only) | 🔒 LOCKED | No early feature creep |

### Do NOT Do:

```
❌ Replace Master V3.1 with HTML Master
❌ Create duplicate factual sources
❌ Return to profile_blocks as authorization
❌ Remove Evidence Matrix
❌ Introduce quota-based selection
❌ Add runtime translation
❌ Replace Jinja with placeholder replacement
❌ Redesign Quality validation before Phase 10
❌ Allow free-form positioning
❌ Change Phase 0/1 scope
```

---

## 10. MINIMAL_INTEGRATION_RECOMMENDATION

### What to do immediately (Phase 0/1 unchanged):
- ✅ Keep all existing architecture
- ✅ Keep all locked principles
- ✅ No code changes during Phase 0/1

### What to document for future phases:
1. **Letter APEC integration** → Design document for Phase 12+
2. **QualityAgentV3 surfaces** → Already designed in locked architecture
3. **A4 visual validation** → Design document for Phase 10
4. **Data-evidence-id attributes** → Design document for Phase 10

### What does NOT belong in job-apply-assistant:
- Akim's specific Master HTML (reference only, not runtime source)
- Akim's manual placeholder system (we use Jinja)
- Akim's fixed positioning (we have Evidence Matrix)

### One-sentence summary:
**Akim's system confirms our architectural choices; no redesign needed.**

---

## Summary Verdict

| Item | Answer |
|------|--------|
| NEW_CV_ARCHITECTURE_REQUIRED | NO |
| NEW_MATCHING_ENGINE_REQUIRED | NO |
| NEW_MASTER_SOURCE_REQUIRED | NO |
| NEW_LETTER_AGENT_REQUIRED | NO |
| EXISTING_LETTER_AGENT_CAN_BE_EXTENDED | YES (Phase 12+) |
| QUALITY_AGENT_CAN_BE_EXTENDED | YES (Phase 10) |
| CURRENT_JINJA_TEMPLATE_REMAINS_AUTHORITY | YES |
| EVIDENCE_MATRIX_REMAINS_CORE | YES |
| DETERMINISTIC_SCORE_REMAINS_CORE | YES |
| MASTER_V3_1_REMAINS_FACTUAL_AUTHORITY | YES |
| PHASE_0_1_SCOPE_REMAINS_UNCHANGED | YES |
| AKIM_IDEAS_CONTRADICT_LOCKED_ARCHITECTURE | NO |

---

**Reconciliation complete. No action required for Phase 0/1.**

**Architecture confirmed resilient. Proceed with Phase 0 baseline capture.**
