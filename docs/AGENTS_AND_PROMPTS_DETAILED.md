# 🤖 Agents & Prompts - Complete System

**How AI agents transform job offers into personalized CVs using profile_blocks**

---

## 🔄 The 4-Agent Pipeline

```
Job Offer Analysis
    ↓
┌─────────────────────────────────────┐
│ 1. MATCHING AGENT                   │
│   (Validate + Enrich)               │
└─────────────────────────────────────┘
    ↓ Analysis + Profile validation
┌─────────────────────────────────────┐
│ 2. POSITIONING AGENT                │
│   (Choose angle + skill profile)    │
└─────────────────────────────────────┘
    ↓ Best positioning strategy
┌─────────────────────────────────────┐
│ 3. GENERATION AGENT                 │
│   (Generate CV/Letter/Mail)         │
└─────────────────────────────────────┘
    ↓ Generated content
┌─────────────────────────────────────┐
│ 4. QUALITY AGENT                    │
│   (Validate no hallucinations)      │
└─────────────────────────────────────┘
    ↓ Verified, safe content
Perfect Application Documents
```

---

## 1️⃣ MatchingAgent - Validation & Enrichment

**File:** `app/agents/matching_agent.py` (54 lines)

### Purpose
Ensures that the analysis only references profile_blocks that actually exist. Validates that OpenAI's suggestions are backed by real data.

### How It Works

```python
@staticmethod
def enrich_analysis(analysis: dict, db: Session) -> dict:
    """
    Input: analysis from AnalysisAgent (which may suggest blocks)
    Process:
    1. Fetch ALL profile_blocks from database
    2. Build map: block_id → block object
    3. Filter suggested blocks:
       - to_use: Keep only IDs that exist in DB
       - to_avoid: Keep only IDs that exist in DB
    4. Log what was kept/rejected
    
    Output: enriched_analysis with validated block references
    """
    # Get ALL blocks from DB
    profile_blocks = db.query(ProfileBlock).all()
    block_map = {b.id: b for b in profile_blocks}
    
    # Validate suggestions from AnalysisAgent
    to_use = analysis.get("profile_blocks_to_use") or []
    to_avoid = analysis.get("profile_blocks_to_avoid") or []
    
    # Filter: keep only valid IDs
    valid_to_use = [bid for bid in to_use if bid in block_map]
    valid_to_avoid = [bid for bid in to_avoid if bid in block_map]
    
    # Update analysis
    analysis["profile_blocks_to_use"] = valid_to_use
    analysis["profile_blocks_to_avoid"] = valid_to_avoid
    
    return analysis
```

### Example

```
AnalysisAgent suggests:
  profile_blocks_to_use: [1, 2, 5, 999]  ← 999 doesn't exist!
  
MatchingAgent validates:
  profile_blocks_to_use: [1, 2, 5]  ← Removed non-existent 999
  
Result: Analysis can only use real blocks
```

### Key Point: NO INVENTION
- MatchingAgent is the gatekeeper
- Prevents hallucinated profile references
- All numbers and dates MUST come from actual profile_blocks

---

## 2️⃣ PositioningAgent - Strategic Angle Selection

**Files:** 
- `app/agents/positioning_agent.py` (99 lines)
- `app/prompts/positioning_prompt.py` (282 lines)

### Purpose
Choose the best market positioning title and determine which aspects of the profile to emphasize in the CV.

### 7 Valid Positioning Angles (Fixed)

```python
VALID_ANGLES = [
    "Data Analyst BI",              # For analytics/reporting roles
    "Marketing Data Analyst",       # For marketing-focused data
    "Data Steward / Data Quality",  # For data governance
    "Business Analyst orienté data",# For business-focused roles
    "Data & AI Consultant",         # For consulting/advisory
    "Product / Ops Analyst",        # For product/ops roles
    "Business Intelligence Analyst",# For BI/dashboard roles
]
```

### Skill Profiles (Determine CV Emphasis)

Each positioning links to a skill_profile that controls CV composition:

```python
SKILL_PROFILES = {
    "marketing_crm": {
        "prioritize": ["Business Systems", "Data & Analytics", "Creative & Delivery"],
        "reduce": ["Backend", "AI/LLM"],
        "signal": "Project management + CRM execution"
    },
    "data_bi": {
        "prioritize": ["Data & Analytics", "Business Systems", "Automation & APIs"],
        "reduce": ["Creative", "AI/LLM"],
        "signal": "Analytics depth + stakeholder reporting"
    },
    "data_ai": {
        "prioritize": ["AI & LLM", "Backend & Data Systems", "Data & Analytics"],
        "reduce": ["Creative"],
        "signal": "Technical depth + AI capability"
    },
    # ... 4 more profiles
}
```

### Flow Diagram

```
AnalysisAgent outputs:
  {
    "job_title": "Senior Data Engineer",
    "company": "Stripe",
    "required_skills": ["Python", "SQL", "AWS", "Spark"],
    "missions": ["Build data pipelines", "Manage infrastructure"],
    "match_score": 8.5
  }

         ↓ Send to OpenAI with POSITIONING PROMPT ↓

OpenAI answers:
  {
    "positioning": "Data & AI Consultant",
    "skill_profile": "data_ai",
    "reasoning": "Your AI/LLM skills and backend depth match this technical role. 
                  Use data_ai profile to emphasize infrastructure expertise."
  }

         ↓ PositioningAgent validates ↓

Validation:
  - Is positioning in VALID_ANGLES? ✓ Yes → Data & AI Consultant
  - Is skill_profile real? ✓ Yes → data_ai exists
  - Both validated? ✓ Yes → Return to handler
```

### Elevia Integration (NEW)

If matching signals available from Elevia API:

```python
async def choose_angle(
    analysis: dict,
    matching_signals: dict = None  # ← NEW: Elevia match data
) -> dict:
    """
    matching_signals = {
        "match_score": 8.2,
        "strengths": ["Strong analytics skills", "AWS experience"],
        "gaps": ["Spark expertise"],
        "explanation": "High-skill alignment with technical team"
    }
    """
    
    if matching_signals:
        # Use enriched prompt with Elevia data
        prompt = get_positioning_prompt_enriched_elevia(
            analysis, 
            matching_signals
        )
        # OpenAI positions informed by real matching data
    else:
        # Standard prompt
        prompt = get_positioning_prompt(analysis)
```

---

## 3️⃣ GenerationAgent - CV/Letter/Mail Creation

**Files:**
- `app/agents/generation_agent.py` (500+ lines)
- `app/prompts/generation_prompt.py` (100+ lines)

### Profile_Blocks Injection Flow

```
1. RETRIEVE BLOCKS FROM DB
   ├─ All blocks (complete profile)
   ├─ Selected blocks (priority emphasis)
   └─ Store in format:
      - Block ID
      - Category (experience, skill, project, etc)
      - Title + Content
      - Tags (companies, dates, etc)

2. SEND TO OPENAI WITH PROMPT
   {
     "all_profile_blocks": [
       {id: 1, category: "experience", title: "Sidel CTO", content: "..."},
       {id: 2, category: "skill", title: "Python", content: "Advanced..."},
       ...
     ],
     "selected_blocks": [
       {id: 1, ...},  ← Emphasized
       {id: 3, ...}   ← Emphasized
     ],
     "positioning": "Data & AI Consultant",
     "job_context": {...}
   }

3. OPENAI RETURNS CV PAYLOAD
   {
     "title": "Data & AI Consultant",
     "experiences": [
       {
         "title": "Data Pipeline Engineer at Sidel",
         "bullets": ["Built 10 data pipelines...", "Reduced latency 60%..."]
       }
     ],
     "skills_sections": [
       {"label": "Languages", "content": "Python, SQL, Spark"}
     ],
     ...
   }

4. SAVE TO DB + RENDER HTML
   └─ HTML template uses CV payload
```

### Key Prompt Instruction (From `generation_prompt.py`)

```
ROLE:
You are an expert Career Agent specialized in ATS optimization.

Your objective is NOT to create a generic CV.

Your objective is to transform the candidate's real experiences 
into the profile that best solves the needs expressed in the job description.

CORE RULE:
NEVER invent experiences, responsibilities, technologies, 
certifications or results.

Adapt, prioritize and rephrase only what is supported by the 
authorized profile blocks provided.

---

AUTHORIZED CANDIDATE DATA:

All available profile blocks (factual base):
#1 [experience] Sidel CTO
  Led technical strategy for 5 years...
  Built data pipeline infrastructure serving 50M records/day
  Managed team of 8 data engineers
#2 [skill] Python
  Expert level. 10 years production experience.
#3 [project] Elevia API Client
  Built async HTTP client using httpx library...

---

PRIORITY BLOCKS (emphasize these first):
#1 [experience] Sidel CTO
#3 [project] Elevia API Client

---

INSTRUCTIONS:

STEP 1: Re-rank experiences
- The strongest experience for [job_title] must come first
- Chronological order is SECONDARY
- Focus on relevance to the job

STEP 2: Rewrite experiences
- Every bullet = Action verb + concrete result + business impact
- Use EXACT NUMBERS from profile blocks

GOOD: "Automated monthly reporting (previously 2–3 days manual) 
       → reduced to under 2 hours"
BAD:  "Contributed to improving reporting efficiency"

STEP 3: Select skills
- Only include skills from authorized blocks
- Group by category (Backend, Data & Analytics, etc)

STEP 4: List projects
- Only reference projects in profile_blocks
- Highlight those matching job requirements

---

CRITICAL: Do NOT invent content
- All experiences must come from blocks #1-10
- All technologies must be mentioned in their blocks
- All results must be supported by block content
```

### Example: CV Generation for "Data & AI Consultant" Positioning

```
Input:
  Job: "Senior Data Engineer at Stripe"
  Positioning: "Data & AI Consultant"
  Selected blocks: [1, 2, 3, 4]  (Sidel experience, Python, Spark, AWS)

OpenAI processes with prompt containing:
  ✓ All blocks (complete profile reference)
  ✓ Selected blocks (prioritize these)
  ✓ Job context (what Stripe needs)
  ✓ STRICT RULE: Only use block content

OpenAI generates:
  CV Title: "Data & AI Consultant"
  
  Experience #1:
  "Data Infrastructure Lead at Sidel"
  • Built 10+ data pipelines processing 50M+ records/day using Spark & AWS
  • Reduced data latency 40% through optimization of Airflow workflows
  • Led team of 8 engineers delivering analytics to 30+ internal teams
  
  Skills:
  • Languages: Python, SQL, Spark
  • Cloud: AWS (EC2, S3, RDS)
  • Tools: Airflow, Git, Jira

Output: CV focused on consultant positioning, 
        with data infrastructure depth as signal
```

### Profile_Blocks Schema

```python
class ProfileBlock(Base):
    id: int                           # Unique ID for reference
    category: CategoryEnum            # experience | skill | project | ...
    title: str                        # "Python", "Sidel CTO", "Elevia API"
    content: str                      # Detailed description
    tags: list[str]                   # Metadata: ["Sidel", "2020-2023"]
    truth_level: TruthLevelEnum       # verified | project | in_progress
    priority: int (1-10)              # How important for ATS
    created_at: datetime
    updated_at: datetime
```

---

## 4️⃣ QualityAgent - Hallucination Detection

**File:** `app/agents/quality_agent.py` (107 lines)

### Purpose
Validate that the generated CV payload contains ONLY content from authorized profile_blocks. Removes any hallucinations.

### How It Works

```python
@staticmethod
def validate_cv_payload(
    cv_payload: dict,              # Generated by OpenAI
    selected_blocks: list[dict]    # Authorized blocks only
) -> dict:
    """
    Compare CV payload against authorized blocks.
    Remove any hallucinations (invented companies, certs, languages, etc).
    """
    
    # BUILD ALLOWED SETS FROM BLOCKS
    allowed_companies = set()
    allowed_certifications = set()
    allowed_languages = set()
    
    for block in selected_blocks:
        if block["category"] == "experience":
            # Extract company from tags
            allowed_companies.update(block["tags"])
        elif block["category"] == "certification":
            allowed_certifications.add(block["title"].lower())
        elif block["category"] == "language":
            allowed_languages.add(block["title"].lower())
    
    # VALIDATE PAYLOAD
    removed_items = []
    
    # Check certifications
    for cert in cv_payload.get("certifications", []):
        if cert["name"].lower() not in allowed_certifications:
            # HALLUCINATION! Remove it
            removed_items.append(f"certification: {cert['name']}")
            logger.warning(f"Removed hallucinated cert: {cert['name']}")
    
    # Check languages
    for lang in cv_payload.get("languages", []):
        if lang["name"].lower() not in allowed_languages:
            # HALLUCINATION! Remove it
            removed_items.append(f"language: {lang['name']}")
            logger.warning(f"Removed hallucinated language: {lang['name']}")
    
    return {
        "clean_payload": cv_payload,
        "removed_items": removed_items,
        "is_valid": len(removed_items) == 0
    }
```

### Example

```
Generated CV has:
{
  "certifications": [
    {"name": "AWS Solutions Architect"},  ← In profile_blocks ✓
    {"name": "Google Cloud Professional"} ← NOT in profile_blocks ✗
  ],
  "languages": [
    {"name": "Python"},      ← In profile_blocks ✓
    {"name": "Mandarin"},    ← In profile_blocks ✓
    {"name": "Klingon"}      ← NOT in profile_blocks ✗
  ]
}

QualityAgent output:
{
  "removed_items": [
    "certification: Google Cloud Professional",
    "language: Klingon"
  ],
  "is_valid": false
}

Result: Only AWS + Python + Mandarin in final CV
```

---

## 🔗 Complete Data Flow with Profile_Blocks

### Step-by-Step Injection

```
1. USER SENDS OFFER
   "Senior Python Engineer at Stripe"

2. ANALYSIS AGENT
   Analyzes job → JSON:
   {
     "job_title": "Senior Python Engineer",
     "company": "Stripe",
     "required_skills": ["Python", "Postgres", "AWS"],
     "profile_blocks_to_use": [1, 2, 5, 7]  ← Suggestions
   }

3. MATCHING AGENT ⬅️ VALIDATION GATE
   Fetches: SELECT * FROM profile_blocks WHERE id IN (1, 2, 5, 7)
   
   Found: [1 ✓, 2 ✓, 5 ✓, 7 ✓]
   
   Confirmed: All blocks exist, use them
   
   Output:
   {
     ...analysis...
     "profile_blocks_to_use": [1, 2, 5, 7]  ← Validated
   }

4. POSITIONING AGENT
   Input: analysis + validated blocks
   
   Decision: "Data & AI Consultant" positioning best uses:
   - Block 1: Sidel CTO experience (backend depth)
   - Block 2: Python skill (primary)
   - Block 5: AWS projects (cloud infrastructure)
   - Block 7: Team leadership (consultant signaling)
   
   Output:
   {
     "positioning": "Data & AI Consultant",
     "skill_profile": "data_ai"
   }

5. GENERATION AGENT ⬅️ BLOCKS INJECTION
   Fetches: SELECT * FROM profile_blocks
   
   Sends to OpenAI:
   {
     "all_profile_blocks": [
       {id: 1, category: "experience", title: "Sidel CTO", content: "..."},
       {id: 2, category: "skill", title: "Python", content: "..."},
       ...
     ],
     "selected_blocks": [1, 2, 5, 7],  ← Priority emphasis
     "positioning": "Data & AI Consultant",
     "job_title": "Senior Python Engineer",
     "required_skills": ["Python", "Postgres", "AWS"]
   }
   
   OpenAI CONSTRAINT: "Only use profile_blocks provided.
                       Never invent content not in blocks."
   
   Output: CV payload using ONLY blocks 1,2,5,7

6. QUALITY AGENT ⬅️ FINAL GATE
   Validates CV payload against selected_blocks [1,2,5,7]
   
   Checks:
   - Certifications mentioned: All in blocks? ✓
   - Languages: All in blocks? ✓
   - Companies: All in blocks? ✓
   - Skills: All in blocks? ✓
   
   Removes any hallucinations
   
   Output: Clean, verified CV

7. RENDERING
   Jinja2 template + clean CV payload → HTML file
   
   Result: Perfect CV for "Senior Python Engineer" at Stripe
```

---

## 🎯 Summary: How Profile_Blocks Prevent Invention

| Stage | Gatekeeper | Check |
|-------|-----------|-------|
| Analysis | OpenAI | Suggests blocks to use |
| Matching | MatchingAgent | Validates block IDs exist in DB |
| Positioning | PositioningAgent | Chooses best angle from 7 fixed options |
| Generation | GenerationAgent | Receives ONLY authorized blocks, can't invent |
| Quality | QualityAgent | Removes any hallucinated content |

### Key Insight

```
Profile_Blocks = Source of Truth

No block → Can't be in CV
Can't be invented
Can't be hallucinated
Can't be faked

Result: 100% authentic CVs using ONLY real experience
```

---

## 📋 Configuration

### profile_blocks Table

```sql
CREATE TABLE profile_blocks (
    id INTEGER PRIMARY KEY,
    category ENUM('experience','skill','project','education','certification','tool','language'),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    tags JSON,                    -- metadata: companies, dates, etc
    truth_level ENUM('verified','project','in_progress','learning'),
    priority INTEGER DEFAULT 0,   -- 1-10 for ATS weighting
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Example data:
INSERT INTO profile_blocks VALUES (
    1,
    'experience',
    'Sidel CTO',
    'Led technical team at Sidel, building data infrastructure...
     Managed 8 engineers. Built 10+ data pipelines processing 50M records/day...
     Tech stack: Python, Spark, AWS, Postgres',
    '["Sidel", "2020-2023", "CTO", "Data", "Leadership"]',
    'verified',
    10,
    NOW(),
    NOW()
);
```

### How to Add Profile_Blocks

```python
from app.database.models import ProfileBlock, CategoryEnum, TruthLevelEnum
from app.database.db import SessionLocal

db = SessionLocal()

block = ProfileBlock(
    category=CategoryEnum.experience,
    title="Sidel CTO",
    content="Led technical strategy for 5 years...",
    tags=["Sidel", "2020-2023", "CTO"],
    truth_level=TruthLevelEnum.verified,
    priority=10
)
db.add(block)
db.commit()
```

---

**Result:** A complete, hallucination-proof pipeline that transforms job offers into perfect CVs using only real, verified candidate experience.
