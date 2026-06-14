# Prompt Architecture Refactor

**Purpose:** Separate concerns cleanly. Make profile_blocks the single source of truth.

**Status:** Implemented

---

## Architecture Overview

```
Offer
  ↓
[AnalysisAgent]
  • Analyze offer only
  • Never rewrite experiences
  • Never create content
  • Return: company, job_title, required_skills, missions, match_score
  ↓
[PositioningAgent]
  • Choose angle from 7 fixed options
  • Use offer analysis for context
  • Return: recommended_positioning + reasoning
  ↓
[GenerationAgent]
  • Transform AUTHORIZED profile blocks into CV
  • Adapt experiences for job relevance
  • Rewrite for business impact
  • CRITICAL: Never invent
  • Return: JSON cv_payload
  ↓
[QualityAgent]
  • Validate payload against profile_blocks
  • Remove hallucinations
  • Build allowed sets (companies, schools, certs, languages)
  • Return: clean_payload + removed_items
  ↓
[Jinja2 Template]
  • Render HTML from clean payload
  • No logic, no validation
  • Trust the payload
  ↓
Telegram
```

---

## 1. AnalysisAgent

**File:** `app/agents/analysis_agent.py`

**Responsibility:** Understand the job offer. Nothing else.

**Inputs:**
- Job offer (raw text)
- All profile_blocks (for reference)

**Process:**
- Parse offer: missions, skills, domain, seniority
- Match against profile_blocks (reference, not content)
- Flag gaps
- Return match_score (0-10)

**Outputs:**
```json
{
  "company": "str",
  "job_title": "str",
  "sector": "str",
  "seniority": "junior|mid|senior|lead",
  "missions": ["mission1", "mission2"],
  "required_skills": ["skill1", "skill2"],
  "soft_skills": ["skill1", "skill2"],
  "ats_keywords": ["keyword1"],
  "business_challenges": "str",
  "match_score": 0-10,
  "strengths": ["strength1"],
  "missing_points": ["gap1"],
  "profile_blocks_to_use": [id1, id2],
  "profile_blocks_to_avoid": [id3]
}
```

**Key Rules:**
- Analyze offer only, do NOT analyze profile content
- Never invent experiences or skills
- Match_score = honest (0-10)
- If skill is missing → put in missing_points

**Where it runs:**
- `app/bot/handlers.py` → `handle_offer()` calls `AnalysisAgent.analyze()`

---

## 2. PositioningAgent

**File:** `app/agents/positioning_agent.py`

**Responsibility:** Choose best positioning from fixed list.

**Inputs:**
- Job analysis (company, job_title, missions, required_skills)

**Process:**
- Evaluate 7 positioning options
- Pick best match
- Provide reasoning

**VALID ANGLES:**
1. Data Analyst BI
2. Marketing Data Analyst
3. Data & AI Project Analyst
4. Automation / AI Workflow Analyst
5. Data Steward / Data Quality
6. Business Analyst orienté data
7. Product / Ops Analyst

**Outputs:**
```json
{
  "recommended_positioning": "Exact angle name",
  "reasoning": "Why this angle matches"
}
```

**Key Rules:**
- Must return exactly one of 7 angles
- Fallback to first option if invalid
- JSON mode (enforced)

**Where it runs:**
- `app/bot/handlers.py` → `handle_offer()` calls `PositioningAgent.choose_angle()`

---

## 3. GenerationAgent

**File:** `app/agents/generation_agent.py`

**Responsibility:** Transform authorized profile_blocks into CV.

**Inputs:**
- Job analysis
- Positioning (from PositioningAgent)
- Selected profile_blocks (from MatchingAgent)
- Candidate info (from config)

**Process:**

### Step 1: Generate CV Payload (JSON mode)
- Prompt includes AUTHORIZED blocks only
- OpenAI rewrites experiences for business impact
- Returns JSON structure

### Step 2: Clean Payload
- Remove markdown/HTML artifacts
- Validate field types

### Step 3: Validate (QualityAgent)
- Check certifications are in blocks
- Check languages are in blocks
- Remove hallucinated items
- Log what was removed

### Step 4: Add Candidate Info
- Name, email, phone, linkedin, github, website
- From config env vars (fallback: empty)

### Step 5: Render Template
- Jinja2 renders HTML
- No validation here (already done)

**Outputs:**
```
HTML file saved to outputs/app_X_cv.html
GeneratedDocument record saved to DB
```

**Key Rules:**
- OpenAI receives ONLY selected blocks
- Prompt explicitly forbids hallucination
- Validation removes ANY item not in blocks
- Log everything removed

**System Prompt Philosophy:**

```
ROLE: Career Agent (transform experiences for job relevance)

CORE: "How can candidate's existing experiences solve this job's problems?"

NEVER:
- Invent experiences
- Fabricate numbers/dates
- Fabricate certifications/companies/schools
- Describe projects as "launched" unless stated

If missing: leave empty
```

**Where it runs:**
- `app/bot/handlers.py` → `handle_command()` calls `GenerationAgent.generate_cv()`

---

## 4. QualityAgent

**File:** `app/agents/quality_agent.py`

**Responsibility:** Detect and remove hallucinations.

**Inputs:**
- Generated cv_payload
- Selected profile_blocks

**Process:**
- Build allowed sets from blocks:
  - `allowed_companies` (from experience tags)
  - `allowed_schools` (from education tags)
  - `allowed_certifications` (from certification blocks)
  - `allowed_languages` (from language blocks)
  - `allowed_tools` (from tool blocks)

- Validate payload:
  - Experiences: allowed (rewritten from blocks)
  - Certifications: remove if not in allowed_certifications
  - Languages: remove if not in allowed_languages
  - Others: allow (no hallucination vectors)

**Outputs:**
```python
{
    "clean_payload": validated_payload,
    "removed_items": ["certification: AWS", "language: Mandarin"],
    "is_valid": bool,
    "hallucination_count": int
}
```

**Key Rules:**
- Conservative: remove ANY item not verifiable from blocks
- Log everything removed
- Experiences are rewritten, so trust them (source is blocks)

**Where it runs:**
- `app/agents/generation_agent.py` → `generate_cv()` calls `QualityAgent.validate_cv_payload()`
- (FUTURE) Can be called from handlers for manual validation

---

## Data Flow

```
User sends offer
        ↓
handle_offer()
  ├─ InputAgent.process() → offer_text
  ├─ create_application()
  ├─ AnalysisAgent.analyze(offer_text)
  │  └─ OpenAI JSON → analysis_json
  ├─ MatchingAgent.enrich_analysis() → validate block IDs
  ├─ save_analysis()
  ├─ PositioningAgent.choose_angle(analysis)
  │  └─ OpenAI JSON → positioning
  └─ format_analysis_summary() → send to Telegram
        ↓
User replies "CV"
        ↓
handle_command()
  ├─ get_last_application()
  ├─ GenerationAgent.generate_cv()
  │  ├─ MatchingAgent.get_selected_blocks()
  │  │  └─ DB: SELECT profile_blocks WHERE id IN (...)
  │  ├─ get_cv_payload_prompt(analysis, blocks, positioning)
  │  ├─ OpenAI (JSON mode) → cv_payload
  │  ├─ _clean_payload() → remove markdown
  │  ├─ QualityAgent.validate_cv_payload() → remove hallucinations
  │  ├─ _build_candidate_info() → add name, email, etc.
  │  ├─ render_cv(context) → Jinja2 → HTML
  │  └─ save_document() + save GeneratedDocument record
  └─ send_document(Telegram)
```

---

## Why This Architecture?

### 1. Separation of Concerns
- AnalysisAgent: Understand job
- PositioningAgent: Choose strategy
- GenerationAgent: Adapt content
- QualityAgent: Validate
- Template: Display

Each does one thing.

### 2. Profile Blocks as Source of Truth
- Only selected blocks enter GenerationAgent
- Prompt explicitly references authorized blocks
- QualityAgent validates against blocks
- Hallucinations caught before rendering

### 3. JSON Mode Throughout
- AnalysisAgent: JSON (structured analysis)
- PositioningAgent: JSON (choice + reasoning)
- GenerationAgent: JSON (CV payload)
- QualityAgent: Python (validation logic)

No ambiguous text free-form outputs (except letter/mail, which are TODO).

### 4. Validation Before Rendering
- OpenAI generates payload
- QualityAgent validates
- Only then Jinja2 renders
- Bad data never reaches template

### 5. Logging & Audit Trail
- Log what AnalysisAgent extracted
- Log what PositioningAgent chose
- Log what GenerationAgent generated
- Log what QualityAgent removed

Full traceability.

---

## Remaining Risks

### Current (Addressed)
✅ CV generation: hallucinations caught by QualityAgent
✅ Analysis: cleaner, offer-focused
✅ Positioning: constrained to 7 options

### To-Do (Future)
- ⚠️ Letter generation: still text free-form (no validation)
- ⚠️ Mail generation: still text free-form (no validation)
- ⚠️ Letter/mail could invent certifications, companies, etc.

**Fix:** Add JSON mode + QualityAgent validation for letter/mail (separate refactor).

---

## Testing the Architecture

### Test 1: Hallucination Detection
```python
# Simulate OpenAI returning invented certification
cv_payload = {
    "certifications": [
        { "name": "AWS Certified Solutions Architect" },  # ← not in blocks
        { "name": "Python for Data Science" }  # ← in blocks
    ]
}

result = QualityAgent.validate_cv_payload(cv_payload, blocks)

assert "AWS Certified" in result["removed_items"]
assert len(result["clean_payload"]["certifications"]) == 1
```

### Test 2: Offer Analysis
```python
# Offer requires "Kubernetes" (not in profile)
# Analysis should flag in missing_points

analysis = AnalysisAgent.analyze(db, "Kubernetes DevOps role")

assert "Kubernetes" in analysis["missing_points"]
assert analysis["match_score"] < 7  # Lower score due to gap
```

### Test 3: Positioning Constraint
```python
# Ensure positioning is always valid

positioning = PositioningAgent.choose_angle(analysis)

assert positioning in [
    "Data Analyst BI",
    "Marketing Data Analyst",
    ...
]
```

---

## Deployment Notes

- No schema changes needed
- Backward compatible with existing DB
- No migration required
- Existing applications can be re-analyzed
- Logs will show "hallucinations_removed=X" (new field)

---

## Future Improvements

1. **Letter/Mail JSON Mode**
   - Add JSON prompts for letter and mail
   - Apply QualityAgent validation

2. **Confidence Scores**
   - Have IA rate confidence per claim
   - Remove low-confidence hallucinations

3. **Audit Dashboard**
   - `/debug_profile` command
   - `/debug_last_analysis` command
   - `/debug_removed_items` command

4. **A/B Testing Prompts**
   - Test different CV generation prompts
   - Measure hallucination rates
   - Optimize for best results

5. **Profile Block Enrichment**
   - Add `dates`, `organization`, `proof_level` fields
   - Better structured profile data
   - Stronger validation

---

**Last updated:** 2026-06-14  
**Refactor commit:** TBD
