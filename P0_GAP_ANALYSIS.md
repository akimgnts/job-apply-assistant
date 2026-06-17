# P0: Gap Analysis + Confidence Scoring

## Why This Matters

Tests on Sopra, Ever.t, and Pelico revealed that the system was missing something fundamental:

**Not understanding the offer better.**

**Measuring the actual mismatch.**

The CV was being adapted without understanding whether the role was even a fit. Gap analysis changes that.

---

## The Problem

### Before: No Gap Measurement
```
Offer → Positioning → CV Adaptation
(no reasoning about gap)
```

Result: CV adapts to any offer equally, creating false confidence in poor fits.

Example (Pelico - Team Lead):
- Offer wants: lead, manage people, architecture
- Akim has: junior-mid individual contributor skills
- Old system: "OK, let's adapt CV to emphasize leadership aspects"
- Result: CV looks deceptive (claims capabilities not held)

### After: Gap Measurement First
```
Offer → Positioning → Gap Analysis → Informed CV Adaptation
                                     (aware of mismatch)
```

Example (Pelico - Team Lead):
- Gap analysis: "Family match good (data engineering), level gap severe (junior vs lead)"
- Confidence: 0.45-0.55 (weak fit)
- CV adaptation informed by this: "Don't claim leadership, emphasize technical foundation"
- Result: Honest CV that sets realistic expectations

---

## Architecture

### GapAnalysisAgent (agents/gap_analysis_agent.py)

Measures mismatch in three dimensions:

```json
{
  "role_family": "data_engineering|marketing|product|ops|finance|automation|governance",
  "required_level": "junior|mid|senior|lead|director",
  "candidate_level": "junior|mid|senior",
  "level_gap": "junior_vs_lead|null",
  
  "must_haves": {
    "SQL": true,
    "Python": true,
    "Team Leadership": false
  },
  
  "nice_to_haves": {
    "Snowflake": true,
    "Power BI": true,
    "Machine Learning": false
  },
  
  "missing_dimensions": [
    "Team leadership experience",
    "People management"
  ],
  
  "bridges": [
    "Data engineering background supports technical roles",
    "Automation experience bridges to process efficiency"
  ],
  
  "fit_factors": {
    "family_match": 0.85,    // Does family match?
    "level_match": 0.50,     // Does level match?
    "skill_match": 0.70,     // Do skills match?
    "seniority_feasible": false
  },
  
  "confidence": 0.62,  // Overall fit score
  "confidence_rationale": "Family matches well, but senior level significantly above current."
}
```

### Confidence Formula

```
confidence = (family_match × 0.5) + (level_match × 0.3) + (skill_match × 0.2)
```

Weights:
- Family (50%): Most important (can't change career mid-stream)
- Level (30%): Important but manageable (can grow into role)
- Skill (20%): Least important (can learn skills)

### Confidence Interpretation

| Score | Meaning | Example |
|-------|---------|---------|
| 0.80-1.00 | Strong fit | Ever.t Data Engineer (family + level match) |
| 0.60-0.79 | Decent fit | Sopra Analytics (family OK, some skill gaps) |
| 0.40-0.59 | Weak fit | Pelico Team Lead (family OK, level gap severe) |
| 0.00-0.39 | Poor fit | Completely wrong career family |

---

## Test Cases (Expected Results)

### 1. Sopra Steria: Consultant Analytics & IA
- Family: data_analytics + data_ai ✓
- Required level: mid-senior
- Candidate level: mid
- Gap: none (aligned)
- Confidence: **0.75-0.85** (strong family match)
- Seniority claim: OK (mid matches mid)
- Bridges: Data analysis, Python/SQL foundation, reporting

### 2. Ever.t: Data Engineer
- Family: data_engineering ✓
- Required level: junior-mid
- Candidate level: mid
- Gap: none (aligned)
- Confidence: **0.80-0.90** (excellent family + level match)
- Seniority claim: OK (mid matches mid)
- Bridges: SQL, Python, data pipeline experience

### 3. Pelico: Team Lead Data Engineering
- Family: data_engineering ✓
- Required level: lead (manage people)
- Candidate level: junior
- Gap: **junior_vs_lead** (severe)
- Confidence: **0.45-0.55** (weak fit)
- Seniority claim: ❌ (cannot claim lead without management experience)
- Bridges: Data engineering background, automation experience
- Message: "Cannot position as lead. Position as individual contributor with technical foundation."

### 4. Marketing Project Manager
- Family: marketing (not data/analytics)
- Required level: mid
- Candidate level: mid
- Gap: family_partial (has reporting, lacks campaign management)
- Confidence: **0.50-0.60** (partial fit)
- Seniority claim: OK (mid matches mid)
- Bridges: Data analysis, reporting, stakeholder coordination
- Message: "Some relevant skills (reporting, coordination), but career pivot required."

---

## Integration

### In GenerationAgent Flow

```python
async def generate_cv(...):
    # ... existing code ...
    
    # 1. Choose positioning
    positioning_result = await PositioningAgent.choose_angle(analysis)
    
    # 2. Analyze gap (NEW - P0)
    gap_assessment = await GapAnalysisAgent.analyze_gap(analysis, positioning)
    logger.info(f"Confidence: {gap_assessment['confidence']}")
    logger.info(f"Level gap: {gap_assessment['level_gap']}")
    
    # 3. Bridge reasoning
    bridge_reasoning = await BridgeEngine.reason_fit(analysis, positioning)
    
    # 4. Adapt CV (informed by gap assessment)
    adaptation = await CVAdaptationAgent.adapt_cv(...)
    
    # ... rest of flow ...
```

### Logged Output

```
INFO: Gap assessment: confidence=0.62, family=data_engineering, level_gap=junior_vs_lead
INFO: Seniority feasible: False
INFO: Bridges: ['Data engineering support', 'Automation expertise']
```

This informs downstream components without breaking them.

---

## Key Rules Enforced

### 1. Family Match
- If offer is "Product Manager" and Akim is data engineer → family mismatch
- Cost: Career pivot needed
- Gap assessment: low confidence

### 2. Level Match
- If offer is "Senior" and Akim is junior → level gap
- Cost: Can be bridged in interview (junior can learn)
- Rule: Don't claim senior in CV (that's dishonest)

### 3. Skill Match
- If offer needs "Machine Learning" and Akim has Python → skill gap
- Cost: Can learn
- Evidence: Foundation present? (Python yes, ML no)

### 4. Bridges (Must Be Credible)
- ✓ "Data engineering background + SQL → can support data pipelines"
- ❌ "Has Python → can be Team Lead" (scope inflation)
- ❌ "Used reporting tools → can be Lead" (authority claim)

### 5. Never Hide Gaps (But Don't Claim Them Either)
- ✓ Log: "confidence=0.45 (weak fit due to level gap)"
- ✓ CV: Position as IC with technical skills (don't claim lead)
- ❌ CV: Claim "led initiatives" (if junior)
- ❌ Hide: Don't acknowledge gap in CV

---

## What Changes Downstream

### PositioningAgent
- Uses confidence score to validate positioning choice
- If confidence < 0.40: maybe choose different angle?

### CVAdaptationAgent
- Knows the confidence score
- Can adapt strategy based on gap:
  - High confidence (0.80+): emphasize strengths
  - Medium confidence (0.60-0.79): emphasize fit + be honest about gaps
  - Low confidence (0.40-0.59): emphasize what exists, don't overreach
  - Poor fit (0.00-0.39): reconsider application

### Handlers (Telegram)
- Could show confidence to user: "Fit level: decent (60%)"
- Warn if low fit: "This is a big career pivot"

---

## Philosophy

> Gap analysis is not about making Akim seem like a bad fit.
> It's about measuring the actual mismatch so CV adapts intelligently.
>
> High confidence → emphasize strengths
> Medium confidence → build explicit bridges
> Low confidence → be honest about gaps
>
> Never hide gaps. Never claim capabilities not held.

---

## Next (P1-P7)

Once P0 (gap analysis) is working:
- P1: Project Narrative Engine (5-7 bullets per project)
- P2: Diversified Summary Engine (10 templates by role family)
- P3: Role Family Detector (family ≠ level)
- P4: Dynamic Skill Ordering (skills order by family)
- P5: OfferUnderstandingAgent (deeper parsing)
- P6: BridgeEngine V2 (enhanced reasoning)
- P7: Experience Balancer (Sidel vs Projects)

But P0 (confidence scoring) is foundation for everything else.

---

## Test

Run:
```bash
python test_gap_analysis.py
```

Expected: Shows 4 test cases with expected confidence ranges.

When database available: Run against real OpenAI API.
