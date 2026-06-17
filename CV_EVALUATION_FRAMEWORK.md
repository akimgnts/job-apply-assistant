# CV Evaluation Framework: 10-Offer Test

## Philosophy

**Best line of code to write: probably no new code.**

MVP is sophisticated enough. Next gain comes from:
```
10 offers → 10 CVs → 10 judgments → Patterns → 1 fix → Re-test
```

Not from adding more agents/prompts.

---

## Primary KPI: Would Send?

**One question**:

```json
{
  "would_send": true
}
```

or

```json
{
  "would_send": false,
  "why_not": [
    "summary too generic",
    "projects under-sold",
    "title not credible"
  ]
}
```

Binary only. No 8.7/10 scores. A perfect title is worthless if you don't send the CV.

---

## Secondary Metrics (If NO)

If `would_send: false`, check:

### 1. Recognizable?

**Q**: Would someone who knows Akim recognize him in this CV?

Values: YES / NO

Detects: False identity, over-transformation, exaggeration.

Example: Pelico Team Lead "led initiatives" → NO (he didn't)

---

### 2. Human?

**Q**: Does this read like a real person?

Values: YES / NO

Detects: ChatGPT-ness, template-speak, "Experienced in delivering...", "Skilled in..."

Example: "Seasoned data expert with extensive expertise" → NO

---

### 3. Career Coherent?

**Q**: Does this tell a credible career story?

Values: YES / NO

Detects: Fake seniority jumps, implausible skill mix, level gaps.

Example:
- Ever.t Data Engineer → YES (natural progression)
- Pelico Team Lead → NO (junior claiming lead)

---

### 4. Technical Details (Secondary)

Only if primary metrics fail, check:

- Title credible?
- Summary level appropriate?
- Sidel substantial (6-7 bullets)?
- Projects credible?
- Red flags (expert, architect, managed, led)?

But these matter only if `would_send: true`.

---

## Evaluation Template

```json
{
  "offer": {
    "company": "Sopra Steria",
    "title": "Consultant Analytics & IA",
    "date": "2026-06-17"
  },
  
  "generated": {
    "positioning": "Data & AI Consultant",
    "confidence": 0.78
  },
  
  "primary_kpi": {
    "would_send": true
  },
  
  "secondary_metrics": {
    "recognizable": true,
    "human": true,
    "career_coherent": true
  },
  
  "why_not": [],
  
  "notes": "Solid CV. Could send to recruiter with confidence."
}
```

If `would_send: false`, always fill `why_not` with specific reasons.

---

## Test Procedure

### For Each Offer (10 times):

1. Generate CV
2. Read carefully (2-3 min, not skim)
3. Fill template above
4. Answer: **would_send?** YES/NO
5. If NO: list **why_not** reasons

### Then:

Collect 10 evaluations.

Count:
- would_send: YES → count
- would_send: NO → analyze why_not

---

## Expected Pattern Analysis

### Best Case (8+ YES)

- Minor issues (maybe 1-2 "projects under-sold")
- MVP validates
- Ready for recruiters

### Mid Case (5-7 YES)

- Clear pattern emerges (e.g., "always exaggerates titles")
- Fix the pattern
- Re-test

### Worst Case (< 5 YES)

- System fundamentally broken
- But at least you **know** what broke
- Fix and iterate

---

## What's Important: The Insight

Your job is not to score 10/10 on every metric.

Your job is to find **why people won't send**.

Examples:
- "Summary too generic" → fix summary templates
- "Recognizable: NO" → you're transforming too much
- "Projects under-sold" → boost project bullets
- "Red flags: 2" → OpenAI is hallucinating forbidden words

Each insight → 1 targeted fix → Re-test.

---

## Timeline

- **Day 1**: Run 3 tests (Sopra, Ever.t, Pelico)
  - Quick assessment. Get immediate feedback.
  
- **Day 2-3**: Run 7 more (varied roles/levels)
  - Find patterns across diversity.
  
- **Day 4**: Analyze
  - What's the #1 issue?
  - Is there a #2?
  
- **Day 5+**: Fix + re-test
  - Not: "implement P2, P3, P4"
  - Yes: "fix the one thing 10 tests revealed"

---

## The Principle

No speculation. No architectural improvements.

Just:
```
Data → Pattern → Fix → Repeat
```

This is how MVPs become real products.
