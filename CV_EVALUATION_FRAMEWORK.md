# CV Evaluation Framework: 10-Offer Test

## Freeze: No New Code (Except This)

MVP is done. Code adds risk now, not value.

**Only** build: evaluation system to measure reality.

---

## 7 Metrics (Checklist + Notes)

### 1. Title

✓ Crédible (recruiter searchs it)
✗ Synthétique (AI-generated nonsense)

Examples:
- ✓ Data Engineer, Data Analyst BI, Consultant Analytics
- ✗ Data Infrastructure Specialist, AI Solutions Expert

**Measure**: Crédible? oui/non

---

### 2. Summary

Trois questions:

- Humain? (reads like real person, not template)
- Crédible? (claims match Sidel facts)
- Niveau? (junior-mid, not overselling)

Examples:
- ✓ "Background in data analysis, reporting, and automation across international teams"
- ✗ "Seasoned data expert with extensive expertise in enterprise-grade systems"

**Measure**: humain/crédible/niveau → oui/oui/ok or non/non/senior_inflation

---

### 3. Sidel Experience

**Question**: Est-ce que Sidel ressemble à une vraie expérience?

Not: polished, perfect, exaggerated.

Yes: substantial, multi-faceted, evidence of depth.

Check:
- ✓ 6-7 bullets (not compressed)
- ✓ Business context preserved (international, B2B)
- ✓ Multi-dimensional (data + reporting + coordination)
- ✓ Tools mentioned (SQL, Power BI, Snowflake)
- ✗ Fake terms (architect, led, managed)

**Measure**: ok/weak/exaggerated

---

### 4. Projects

**Question**: Sont-ils sous-vendus ou sur-vendus?

Check:
- Elevia: 2 bullets, credible?
- Job Apply Assistant: 2 bullets, credible?
- V.I.E Matcher: 1 bullet, sufficient?
- Total: ≤5 bullets

Avoid:
- ✗ "Startup-scale solution"
- ✗ "Reached 1M users"
- ✗ "Architected platform"

Target:
- ✓ "Built document canonicalization + scoring for job matching"
- ✓ "Telegram bot integrating OpenAI for CV generation"

**Measure**: oversold/undersold/ok

---

### 5. Skills Order

**Question**: L'ordre est-il cohérent avec le positionnement?

For Data Engineer: Backend + Data + Automation should lead.
For Marketing: Business + Data + Creative should lead.

Check:
- First 3 skill sections match positioning
- Order makes sense (not random)
- No weird ranking

**Measure**: coherent/incoherent

---

### 6. Red Flags

Scan for forbidden words:

- expert
- architect
- managed
- led
- scalable platform
- enterprise-grade
- robust and scalable
- world-class
- cutting-edge
- extensive experience

**Measure**: red_flags_count (0 = good, 1+ = problem)

---

### 7. The Ultimate Test

**Simple question**:

> "Would I actually send this CV to a recruiter?"

No 7.8/10 scores.

Binary:
- YES (send)
- NO (rework needed)

---

## Evaluation Template

```json
{
  "offer_company": "Sopra Steria",
  "offer_title": "Consultant Analytics & IA",
  "positioning_generated": "Data & AI Consultant",
  "confidence_score": 0.78,
  
  "evaluation": {
    "title": {
      "credible": true,
      "notes": "Data & AI Consultant is real market title"
    },
    "summary": {
      "humain": true,
      "credible": true,
      "niveau": "mid",
      "notes": "No exaggeration, sounds authentic"
    },
    "sidel": {
      "quality": "ok",
      "bullet_count": 7,
      "business_context_preserved": true,
      "multidimensional": true,
      "notes": "Good balance of data, reporting, coordination"
    },
    "projects": {
      "elevia": 2,
      "job_apply_assistant": 2,
      "vie_matcher": 1,
      "total": 5,
      "quality": "ok",
      "notes": "Projects support without overshadowing"
    },
    "skills": {
      "order": "coherent",
      "matches_positioning": true,
      "notes": "Data & Analytics leads, reasonable for consultant role"
    },
    "red_flags": {
      "count": 0,
      "words_found": []
    },
    "would_send": true,
    "notes": "Solid CV. Confident enough to send. Only minor issues if any."
  }
}
```

---

## Test Procedure

### For Each Offer (10 times):

1. Copy offer text/URL
2. Feed to Job Apply Assistant
3. Generate CV
4. **Download HTML**
5. **Read carefully** (not skim)
6. **Fill evaluation form** above
7. **Note issues** in "notes" field
8. **Judge**: would_send = yes/no

### Then:

Collect 10 evaluations.

Analyze patterns:
- What keeps failing?
- What works well?
- What surprises?
- Which metrics matter most?

---

## What NOT to Do

❌ Add new agents
❌ Tweak prompts speculatively
❌ Optimize for metrics
❌ Add new code features

## What to Do

✅ Run 10 tests
✅ Collect honest evaluations
✅ Spot patterns
✅ Fix only what's broken

---

## Expected Outcomes

### Best Case
- 8-10 CVs would send
- Minor tweaks needed
- MVP validation complete
- Ready to show to recruiters

### Worst Case
- 3-5 CVs would send
- Major pattern identified (e.g., "always oversells")
- Clear fix identified
- Iterate + re-test

### Either way
You now have **data**, not speculation.

---

## Next: Based on Results

Not: "Let's add P2, P3, P4..."

Yes: "10 tests show pattern X. Fix X. Re-test."

That's iteration. That's product development.

---

## Tool: Evaluation Checklist (Copy-Paste)

```
Offer: [Company] - [Title]
Positioning: [Generated title]
Confidence: [Score]

Title Credible? ☐ yes ☐ no → Notes:
Summary Human? ☐ yes ☐ no → Notes:
Summary Credible? ☐ yes ☐ no → Notes:
Summary Level? ☐ ok ☐ overselling → Notes:
Sidel Quality? ☐ ok ☐ weak ☐ exaggerated → Notes:
Projects? ☐ ok ☐ undersold ☐ oversold → Notes:
Skills Order? ☐ coherent ☐ incoherent → Notes:
Red Flags? ☐ 0 ☐ 1+ → Count:

Would Send? ☐ YES ☐ NO

Overall Notes:
```

---

## Why This Works

1. **Reality check**: Tests against real offers, not theory
2. **Human judgment**: What matters to actual humans (send/no-send)
3. **Pattern detection**: 10 data points reveal what to fix
4. **No speculation**: You see actual problems, not imagined ones
5. **Direction**: Results say "fix X, not Y"

---

## Timeline

- Day 1: Run 3 tests (Sopra, Ever.t, Pelico)
- Day 2-3: Run 7 more tests (varied)
- Day 4: Analyze results
- Day 5+: Iterate based on patterns

Not: "Implement P2, P3, P4 first, then test"

Yes: "Test first. Results tell you what to build next"
