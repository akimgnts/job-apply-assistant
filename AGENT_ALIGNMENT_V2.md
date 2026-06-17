# Agent Alignment V2: Build Bridges, Not Identities

## Philosophy

**The objective is NOT to transform Akim into the ideal candidate.**

**The objective is to explain why Akim makes sense for this role while remaining 100% truthful.**

The system must build bridges, not identities.

---

## Core Principles

### 1. Truth is Immutable

What cannot change:
- Companies, dates, roles (never fabricated)
- Technologies must exist in Master CV
- Achievements must be real and provable
- No invented metrics, percentages, or certifications
- No false claims of responsibility
- Seniority comes from reality, never inherited from offer

### 2. Narrative is Flexible

What can change:
- Wording (clarity + relevance)
- Emphasis (highlight what matters, downplay noise)
- Vocabulary (adapt to role domain)
- Tone (technical → business, etc)
- Signal > noise, substance > brevity

### 3. Candidate Remains Recognizable

Never collapse profile into single domain.

Akim is:
- Data + Analytics + Automation + Business + Communication

All dimensions are strengths. Do NOT erase them.

---

## Architecture Flow

### Before: Transform Candidate
```
Offer → [Transform] → Candidate → Generate CV
❌ Wrong: Creates false identity
```

### After: Bridge to Role
```
Offer
  ↓
Understand Business Need
  ↓
Evaluate Candidate Reality (BridgeEngine)
  ↓
Build Bridges (where strengths meet needs)
  ↓
Generate Positioning
  ↓
Adapt CV (preserve identity, emphasize fit)
```

---

## Components

### 1. BridgeEngine (agents/bridge_engine.py)

Explicit reasoning before CV adaptation.

**Questions answered**:
1. What business problem does the role solve?
2. What does Akim actually possess?
3. Where are the overlaps?
4. Where are the gaps?
5. Can we build bridges without inventing experience?

**Output** (logged, informs adaptation):
```json
{
  "business_problem": "What company solves",
  "primary_strengths": ["Strength with evidence"],
  "gaps": ["Gap 1", "Gap 2"],
  "bridges": ["How strength X addresses problem Y"],
  "seniority_assessment": "Junior|Mid|Senior",
  "positioning_rationale": "Why positioning makes sense"
}
```

**Rules**:
- Do NOT compensate gaps with invented experience
- Do NOT claim titles Akim never held
- Do NOT inflate scope
- Be honest about misalignment
- Gaps are acceptable. Lies are not.

---

### 2. SummaryVocabulary (prompts/summary_vocabulary.py)

Prevents exaggeration in CV summary.

**Forbidden words** (sound expert/overqualified):
- expert, extensive experience, architected, managed, owned, mentored, led
- enterprise-grade, robust and scalable, advanced expertise, seasoned
- specialist in, driving, spearheaded, pioneer, world-class, cutting-edge

**Preferred words** (sound junior-mid, authentic):
- background in, exposure to, worked on, contributed to, supported
- experience across, combining, focused on, collaborated with, helped deliver
- participated in, involved in, familiar with, skilled in, hands-on experience

**Effect**: CV sounds like someone who did real work, not someone trying to convince.

---

### 3. PositioningAgent (agents/positioning_agent.py)

Only real market titles. No synthetic AI-generated titles.

**Valid angles** (recruiters search for these):
1. Data Analyst BI
2. Marketing Data Analyst
3. Data Steward / Data Quality
4. Business Analyst orienté data
5. Data & AI Consultant
6. Product / Ops Analyst
7. Business Intelligence Analyst

**Invalid** (❌ never use):
- Data Infrastructure Engineer (too specific, not searchable)
- Customer Experience Marketing Analyst (made-up)
- Solution Engineer Focused on Automation (jargon)
- AI Solutions Specialist (marketing speak)
- Team Lead (authority claim if not held)

---

### 4. AdaptationPrompt (prompts/adaptation_prompt.py)

Updated to preserve identity + enforce vocabulary.

**Key rules**:
- Never compress Sidel experience excessively
- Preserve multi-dimensional nature (6-7 bullets for Sidel)
- Summary: 70 words, junior-mid tone, authentic
- Experience order: FIXED [0, 1, 2] (never changes)
- Projects: substantive, not toy projects
- Skills support positioning (don't define it)

---

## Forbidden Patterns

### ❌ Synthetic Titles
```
"Customer Experience Marketing Analyst"
"Data Infrastructure Engineer"
"AI Solutions Specialist"
```

### ❌ Exaggerated Summaries
```
"Seasoned data expert with extensive experience architected enterprise-grade
data pipelines and drove advanced AI solutions for teams across Europe."
```

### ❌ Compressed Identity
```
"Data engineer with expertise in Python and SQL"
→ Erases business, communication, automation, stakeholder dimensions
```

### ❌ Seniority Inheritance
```
Offer: Team Lead
CV: "Led initiatives, managed teams, drove strategy"
❌ WRONG (if not held)
```

### ❌ Invented Experience
```
"Architected Snowflake data warehouse"
(if only used it, didn't design it)
```

---

## What Stays True

### Profile Identity
Akim's multi-dimensional nature is a strength, not noise:
- Data quality and consolidation
- Reporting and stakeholder visibility
- Business understanding
- International coordination
- Automation and process improvement
- Communication and cross-functional work

### Flagship Experience (Sidel)
- 6-7 bullets minimum (not compressed)
- 40-50% of experience section
- Preserves: international, B2B, stakeholders, coordination, tools, impact
- Shows: maturity, depth, breadth, credibility

### Projects
- Substantive, not toy projects
- Real technology choices
- Real problem-solving
- Evidence of capability

---

## Tests for Alignment V2

### Test 1: Personal Recognition
**Question**: Would someone who knows Akim personally still recognize him in the CV?

**If NO** → adaptation has gone too far. Reduce transformation, increase bridges.

**Example**:
- ✅ "Data analyst with background in automation and business reporting" → Still recognizable
- ❌ "Senior Data Architect leading enterprise ML initiatives" → False identity

### Test 2: Truth Claim
**Question**: Could Akim defend every claim in the CV if asked directly?

**If NO** → too much narrative. Tone down.

**Example**:
- ✅ "Worked on data consolidation from multiple sources using SQL and Python"
- ❌ "Architected scalable data infrastructure"

### Test 3: Vocabulary Check
**Question**: Does summary contain forbidden words?

**If YES** → too much exaggeration. Rewrite.

**Example**:
- ✅ "Experience combining data analysis, reporting, and stakeholder coordination"
- ❌ "Extensive expertise in advanced data analytics"

### Test 4: Gap Honesty
**Question**: Are gaps acknowledged or hidden?

**If HIDDEN** → CV looks dishonest. Acknowledge and bridge instead.

**Example**:
- ✅ Bridge: "Lacks direct ML experience but has Python + API integration background"
- ❌ Hide: Don't mention ML gap, pretend expertise

---

## Implementation

### GenerationAgent Flow
```python
async def generate_cv(...):
    1. Load Master CV (truth source)
    2. Call BridgeEngine (reason about fit)
    3. Call CVAdaptationAgent (adapt with bridges in mind)
    4. Validate adaptation (no hallucinations)
    5. Ensure defaults (title, summary)
    6. Validate HTML (no None/null)
    7. Render + save
```

### Bridge reasoning informs but doesn't dictate
- Bridges logged for transparency
- Gaps logged to inform what NOT to claim
- Adaptation still uses OpenAI, but with constraints
- Final HTML validation ensures no exaggeration leaked through

---

## Philosophy Preserved

✅ **Skill Profiles** - unchanged (7 profiles, each supports a positioning)
✅ **Narrative Engine** - enhanced (now respects truth + vocabulary constraints)
✅ **Prompts** - enhanced (vocabulary enforcement, identity preservation)
✅ **Architecture** - unchanged (agents still pure, no refactoring)

Only the **philosophy** is clarified, not the code structure.

---

## Why This Matters

**For users**:
- CVs that actually reflect who they are
- More credible to recruiters
- Better alignment = better conversations
- Gaps don't disqualify if bridges are clear

**For system**:
- Avoids hallucination + false claims
- Reduces hiring agent confusion
- Improves candidate-role fit quality
- Builds sustainable trust

**For truth**:
- Facts never invented
- Claims always defensible
- Narrative adapts without lying
- Bridges connect, not compensate

---

## Examples

### Example 1: Data Engineer Offer (Akim is Junior)

❌ **OLD** (invents identity):
```
Title: Data Infrastructure Engineer
Summary: Extensive expertise in architected scalable data systems
Experience: Completely rewritten to hide junior status
```

✅ **NEW** (builds bridges):
```
BridgeEngine reasoning:
- Problem: Company needs someone to improve data pipelines
- Strength: Akim has SQL, Python, has used Snowflake
- Gap: Junior, hasn't architected from scratch
- Bridge: Experience consolidating multi-source data + technical foundation

Title: Data & AI Consultant (real market title)
Summary: Data-oriented profile combining data consolidation, Python/SQL,
         and cross-functional coordination
Experience: Preserved 6-7 bullets on Sidel, emphasize: data quality + tools
           Don't claim: architecture, database design, infrastructure ownership
```

### Example 2: Marketing Project Manager Offer

❌ **OLD** (overwrites profile):
```
Title: Marketing Project Manager
Experience: Remove all technical content, focus only on "management"
Skills: Hide data, analytics, automation
```

✅ **NEW** (builds bridges):
```
BridgeEngine reasoning:
- Problem: Need someone to coordinate marketing campaigns + reporting
- Strength: Akim has CRM exposure, project coordination, reporting experience
- Gap: Not a career marketer, limited campaign management
- Bridge: Spreadsheet/reporting + stakeholder coordination experience applies

Title: Marketing Data Analyst (real market title - bridges both domains)
Summary: Background in data reporting and stakeholder coordination
Experience: Highlight Sidel bullets on: cross-functional work, reporting,
           business understanding. Include automation / process improvement.
Skills: Emphasize Business Systems + Data & Analytics (CRM tools, reporting)
```

---

## Key Takeaway

> The goal is NOT to make Akim seem perfect.
> The goal is to explain why Akim still makes sense despite gaps.
>
> Truth immutable. Narrative flexible. Build bridges, not identities.
