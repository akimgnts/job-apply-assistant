# Prompt Architecture

Job Apply Assistant uses **4 main prompts** in sequence to analyze offers, position candidates, and generate documents.

**Philosophy:** Truth is immutable. Narrative is flexible.
- Facts (companies, dates, roles, achievements) cannot be fabricated
- Bullets can be rewritten for clarity, relevance, and positioning
- Weak bullets removed, strong bullets amplified
- Goal: Premium positioning engine, not ATS keyword optimizer
- CV must feel human, credible, founder-readable (30-second test)

**Status:** Production-ready

---

## Pipeline Overview

```
Job Offer (URL/text)
    ↓
[1. ANALYSIS] → Job analysis JSON
    ↓
[2. POSITIONING] → Positioning angle (1 of 7)
    ↓
[3. ADAPTATION] → Adaptation payload (bullets, projects, summary)
    ↓
[4. QUALITY CHECK] → Validation report
    ↓
Generated CV + Letter + Mail
```

---

## Prompt 1: Analysis (`app/prompts/analysis_prompt.py`)

**Purpose:** Extract structured job requirements and match against candidate profile.

**Agent:** `AnalysisAgent.analyze()`

**Input:**
- Job offer text (URL-extracted or user-pasted)
- All candidate profile blocks (experiences, skills, education)

**Output:** JSON with:
```json
{
  "company": "Company name",
  "job_title": "Job title",
  "sector": "Industry",
  "seniority": "junior/mid/senior/lead",
  "missions": ["Main responsibility 1", "Main responsibility 2"],
  "required_skills": ["Skill 1", "Skill 2"],
  "soft_skills": ["Soft skill 1"],
  "ats_keywords": ["Keyword1", "Keyword2"],
  "business_challenges": "What problems this role solves",
  "match_score": 0-10,
  "strengths": ["Why candidate fits"],
  "missing_points": ["Gap 1"],
  "profile_blocks_to_use": [1, 2, 3],
  "profile_blocks_to_avoid": [4, 5]
}
```

**Rules (CRITICAL):**
- Analyze offer only — do not rewrite candidate content
- Never invent experiences/skills
- match_score = honest 0-10 assessment
- If skill missing from profile → put in missing_points
- profile_blocks_to_use = indices of best matching blocks

---

## Prompt 2: Positioning (`app/prompts/positioning_prompt.py`)

**Purpose:** Choose best positioning angle from 7 fixed options.

**Agent:** `PositioningAgent.choose_angle()`

**Input:**
- Job analysis JSON
- 7 predefined positioning angles (e.g., "Data Analyst BI", "Growth Marketer", etc.)

**Output:** One positioning string selected from the 7 options.

**Rules:**
- Choose only from predefined angles — never create new ones
- Base choice on job requirements + match_score
- Positioning guides CV/letter customization
- Must align with candidate's Master CV strengths

---

## Prompt 3: Adaptation (`app/prompts/adaptation_prompt.py`) ★ CRITICAL

**Purpose:** Adapt Master CV to job offer. **Philosophy: Truth is immutable. Narrative is flexible.**

**Agent:** `CVAdaptationAgent.adapt_cv()`

**Input:**
- Job analysis JSON
- Positioning angle (from Prompt 2)
- Master CV structure (facts are source of truth)

**Output:** Adaptation JSON with rewritten/selected bullets:
```json
{
  "title": "Adapted positioning title (max 8 words)",
  "summary": "" or "Rewritten summary (max 70 words)",
  "experience_order": [0, 1, 2],
  "experience_bullets": {
    "0": ["Rewritten Sidel bullet 1 (fact-based, relevant)", "Rewritten Sidel bullet 2", "..."],
    "1": ["Rewritten MadeByAkim bullet 1", "Rewritten MadeByAkim bullet 2"],
    "2": ["Rewritten Vassard bullet 1"]
  },
  "project_order": [0, 1, 2],
  "project_bullets": {
    "0": ["Rewritten Elevia description (fact-based)"],
    "1": ["Rewritten Job Apply Assistant description"],
    "2": ["Rewritten V.I.E Matcher description"]
  },
  "ats_keywords": ["Keyword1", "Keyword2"]
}
```

**Allowed Changes (FLEXIBLE NARRATIVE):**
- ✅ Rewrite bullets for clarity and relevance
- ✅ Remove weak or irrelevant bullets
- ✅ Amplify strong bullets that support positioning
- ✅ Adapt vocabulary to match role domain
- ✅ Simplify jargon or reorganize facts
- ✅ Reorder bullets within each experience by relevance
- ✅ Reorder projects by relevance
- ✅ Adapt title
- ✅ Rewrite summary (max 70 words, optional)
- ✅ Select ATS keywords

**Forbidden (IMMUTABLE TRUTH):**
- ❌ Invent companies, dates, roles, achievements, certifications
- ❌ Fabricate metrics or percentages
- ❌ Add technologies not in Master CV
- ❌ Create new experiences
- ❌ Reorder experiences (fixed: Sidel [0] → MadeByAkim [1] → Vassard [2])
- ❌ Claim credit for work not done

**Validation:** `validate_adaptation()` enforces:
- experience_order must be exactly [0, 1, 2]
- Facts preserved (no fabrications)
- Bullets exist for each experience (can be rewritten/removed/reordered)
- All 3 required projects present (0, 1, 2)
- Optional 4th project (SkillMap, id 3) only for AI/Product/Visualization/Automation roles

**Style Guidelines:**
- Clarity beats complexity
- Relevance beats exhaustiveness
- Signal beats noise
- Credibility beats keyword stuffing
- Avoid: ChatGPT tone, buzzwords, generic language
- Use: confidence, simplicity, clarity, directness

---

## Prompt 4: Quality Check (`app/prompts/quality_prompt.py`)

**Purpose:** Validate generated documents for hallucinations and inconsistencies.

**Agent:** `QualityAgent.check_document()`

**Input:**
- Generated CV/letter/mail HTML
- Master CV (source of truth)
- Original job analysis

**Output:** Quality report with:
```json
{
  "status": "SAFE" | "REVIEW" | "REJECT",
  "issues": ["List of detected issues"],
  "flags": ["Warnings for review"],
  "confidence": 0-1
}
```

**Checks:**
- No invented companies/schools/certifications
- No fabricated achievements or metrics
- All content originates from Master CV
- Dates/numbers unchanged
- Tone and language appropriate for business/finance

---

## Master CV Service (`app/services/master_cv_service.py`)

**Purpose:** Provide immutable source of truth for all CV content.

**Load:** `load_master_cv()` returns:
```python
{
  "personal_info": {
    "name": "Akim Guentas",
    "location": "Paris",
    "email": "akimguentas13@gmail.com",
    "phone": "+33...",
    "portfolio": "madebyakim.com",
    "github": "github.com/akimgnts",
    "linkedin": "linkedin.com/in/akimguentas"
  },
  "experiences": [
    { 
      "id": 0, 
      "title": "Data, Marketing & Communication Analyst (Apprenticeship)",
      "company": "Sidel",
      "context": "International B2B industrial environment",
      "dates": "2023 – 2025",
      "bullets": [8 business-oriented bullets]
    },
    { 
      "id": 1,
      "title": "Freelance Projects · Data, Automation & Digital Systems",
      "company": "MadeByAkim / Made By Curve",
      "dates": "2024 – Present",
      "bullets": [6 bullets]
    },
    {
      "id": 2,
      "title": "Business Development & Reporting",
      "company": "Vassard OMB Mobilier",
      "dates": "2022 – 2023",
      "bullets": [3 bullets]
    }
  ],
  "projects": [
    { "id": 0, "title": "Elevia · Personal Data & AI Project", ... },
    { "id": 1, "title": "Job Apply Assistant", ... },
    { "id": 2, "title": "V.I.E Matcher", ... },
    { "id": 3, "title": "SkillMap Automation Console", ... }  # optional
  ],
  "skills": [6 skill sections],
  "education": [3 degrees, formatted with graduation year only],
  "certifications": [3 certs],
  "languages": [3 languages],
  "experiences_by_id": { 0: ..., 1: ..., 2: ... },
  "projects_by_id": { 0: ..., 1: ..., 2: ..., 3: ... }
}
```

**Key Properties:**
- All content verified (no hallucinations)
- Bullet count fixed per experience
- Education year format: graduation year only (e.g., "2025")
- Personal info: real values, no placeholders
- experiences_by_id + projects_by_id dicts for template access

**Validation:** `validate_adaptation()` checks:
- All bullets present and unchanged
- Projects contain required 3 ([0, 1, 2])
- experience_order is exactly [0, 1, 2]
- SkillMap (3) only when role-appropriate

---

## Content Philosophy

### Truth is Immutable. Narrative is Flexible.

**Immutable (Facts):**
- Companies, dates, roles, achievements
- Education and certifications
- Technologies used
- Metrics and results (if real)

**Flexible (Narrative):**
- Wording and emphasis
- Bullet selection and ordering
- Vocabulary adaptation (e.g., BI → analytics, automation → workflow)
- Tone and language (technical → business, ops → finance)
- Weak bullet removal, strong bullet amplification

### Premium Positioning, Not ATS Optimization

- **Goal:** Maximize credibility, relevance, positioning, clarity
- **Test:** Founder/hiring manager understands value in 30 seconds?
- **Style:** Confidence, simplicity, directness
- **Avoid:** Buzzwords, keyword stuffing, ChatGPT tone, generic language
- **Principle:** Signal beats noise. Relevance beats exhaustiveness.

### Business/Finance Orientation

Master CV refined for professional CVs (not startup/tech):
- **Action verbs:** analyze, consolidate, structure, monitor, coordinate, present
- **Avoid:** built, created, developed (too casual/technical)
- **Summary:** optional (empty for finance/business roles — experience speaks for itself)
- **Education:** graduation year only (e.g., "Eugenia School — 2025")
- **School name:** "Eugenia School" (not "École Gamma")
- **Projects:** 3 default [0, 1, 2] + 1 optional (SkillMap for AI/Product/Visualization roles)

---

## Integration in Agents

| Agent | Prompts Used | Input | Output |
|-------|-------------|-------|--------|
| **InputAgent** | None | URL/text | Extracted job offer text |
| **AnalysisAgent** | Prompt 1 | Offer + profile blocks | Analysis JSON |
| **MatchingAgent** | None | Analysis | Validated profile blocks |
| **PositioningAgent** | Prompt 2 | Analysis | Positioning angle |
| **CVAdaptationAgent** | Prompt 3 | Analysis + positioning + Master CV | Adaptation payload |
| **GenerationAgent** | None | Adaptation + Master CV | Rendered HTML (CV/letter/mail) |
| **QualityAgent** | Prompt 4 | Generated HTML + Master CV | Safety report |

---

## Common Tasks

### Test Analysis Prompt

```python
from app.prompts.analysis_prompt import get_analysis_prompt
from app.services.openai_service import analyze_offer

prompt = get_analysis_prompt(job_offer_text, profile_blocks)
analysis = analyze_offer(prompt)
print(analysis)
```

### Test Adaptation Prompt

```python
from app.prompts.adaptation_prompt import get_cv_adaptation_prompt
from app.services.openai_service import generate_cv_payload
from app.services.master_cv_service import load_master_cv

master = load_master_cv()
prompt = get_cv_adaptation_prompt(analysis, positioning, master)
adaptation = generate_cv_payload(prompt)
print(adaptation)
```

### Verify Master CV

```python
from app.services.master_cv_service import load_master_cv

master = load_master_cv()
for exp in master["experiences"]:
    print(f"{exp['company']}: {len(exp['bullets'])} bullets")
    
for proj in master["projects"]:
    print(f"{proj['title']}: {len(proj['bullets'])} bullet(s)")
```

### Test Adaptation Validation

```python
from app.services.master_cv_service import validate_adaptation

result = validate_adaptation(adaptation_json, master_cv)
if result["is_valid"]:
    print("✓ Adaptation passed validation")
else:
    print("✗ Issues found:")
    for issue in result["issues"]:
        print(f"  - {issue}")
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `app/prompts/analysis_prompt.py` | Prompt 1: Job analysis |
| `app/prompts/positioning_prompt.py` | Prompt 2: Positioning angle |
| `app/prompts/adaptation_prompt.py` | Prompt 3: Master CV adaptation |
| `app/prompts/quality_prompt.py` | Prompt 4: Quality validation |
| `app/services/master_cv_service.py` | Master CV storage + validation |
| `app/agents/analysis_agent.py` | Executes Prompt 1 |
| `app/agents/positioning_agent.py` | Executes Prompt 2 |
| `app/agents/cv_adaptation_agent.py` | Executes Prompt 3 |
| `app/agents/quality_agent.py` | Executes Prompt 4 |
| `app/agents/generation_agent.py` | Orchestrates CV/letter/mail rendering |

---

## Future Enhancements

- [ ] Prompt caching (reduce OpenAI API calls)
- [ ] Fine-tuned models (custom positioning angles)
- [ ] A/B testing different adaptation strategies
- [ ] Multi-language support (FR/ES/DE prompts)
- [ ] Dynamic positioning (learned from user feedback)
- [ ] Master CV versioning (maintain multiple versions)

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
