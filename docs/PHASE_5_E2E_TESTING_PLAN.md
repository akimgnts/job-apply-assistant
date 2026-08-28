# Phase 5: End-to-End Testing & Quality Optimization

**Status**: Planning  
**Goal**: Verify the complete pipeline produces factually sound, useful CVs across diverse job families.

## Philosophy

Phase 4 ensured **hallucination-free** claims. Phase 5 ensures **quality CVs**:
- Not over-cleaned (≥80% retention)
- Well-adapted to the job family
- Proper block matching
- Minimized false negatives

## Test Cases (5 Job Families)

### 1. Data Analyst / BI (Natural Fit)
- **Profile match**: Excellent (Sidel direct mapping)
- **Expected outcome**: High pass rate, minimal removals
- **Focus**: Verify Sidel blocks are correctly matched and validated

### 2. Business Analyst (Moderate Fit)
- **Profile match**: Partial (needs bridge reasoning)
- **Expected outcome**: Moderate pass rate, some rewrites
- **Focus**: Test gap analysis + bridge engine integration

### 3. Automation / AI Engineer (Good Fit)
- **Profile match**: Good (MadeByAkim + Elevia)
- **Expected outcome**: High pass rate, Elevia blocks well-matched
- **Focus**: Verify project blocks work correctly

### 4. Marketing / Growth (Weak Fit)
- **Profile match**: Weak (few matching technologies)
- **Expected outcome**: Low pass rate, controlled REVIEW recommendations
- **Focus**: Test graceful degradation, no false positives

### 5. Tech Lead / Engineering Manager (Low Fit)
- **Profile match**: Misaligned (leadership role, not IC)
- **Expected outcome**: REJECT or heavy REVIEW
- **Focus**: Verify system knows when to refuse

## Metrics Collected Per CV

### Validation Metrics
- `pass_count` (claims with no issues)
- `rewrite_count` (claims corrected)
- `remove_count` (claims removed)
- `removal_rate` (% removed = remove_count / total_claims)
- `qc_recommendation` (ACCEPT / REVIEW / REJECT)

### Content Retention
- `bullets_before` (count after CVAdaptationAgent)
- `bullets_after` (count after QualityAgent v2)
- `retention_rate` (bullets_after / bullets_before)
- `avg_bullet_length_before` / `after`
- `experiences_included`, `projects_included`, `skills_sections`

### Block Matching Quality
- `blocks_searched` (total blocks examined)
- `best_match_found` (% of bullets where best match ≠ fallback)
- `top_matched_blocks` (which source_refs matched most)
- `match_confidence_scores` (internal rating by heuristic)

### HTML Quality
- `html_validation_issues` (count of warnings)
- `ats_keywords_count`
- `summary_present` (bool)
- `rendering_errors` (None, null, empty sections)

### False Negatives (Manual Review)
- Claims that **SHOULD HAVE PASSED** but were removed
- Claims that **SHOULD HAVE BEEN REWRITTEN** but kept verbatim
- Categorized by reason: tech mismatch, metric mismatch, status, proficiency

## Success Criteria

### ✅ Pass (Ready for Production)
- **Zero hallucinations detected** (manual review confirms)
- **Removal rate < 25%** across all test cases
- **Retention rate ≥ 80%** (most bullets survive)
- **No REJECT recommendations** or 1 max (weak match case)
- **False negatives < 30%** (acceptable false alarm rate)
- **Block matching success ≥ 85%** (heuristic finds right block)

### ⚠️ Review (Address Issues Before Production)
- Removal rate 25–40%
- Retention rate 60–80%
- 1–2 REJECT recommendations
- False negatives 30–50%
- Some block matching failures (< 15%)

### ❌ Fail (Major Issues to Fix)
- Hallucinations detected
- Removal rate > 40%
- Retention rate < 60%
- All test cases REJECT
- False negatives > 50%
- Block matching < 70%

## Diagnostics Strategy

If Phase 5 fails, identify root cause:

| Symptom | Likely Cause | How to Diagnose |
|---------|-------------|-----------------|
| High removal_rate | Validator too strict? Missing blocks? | Compare against frozen block metrics |
| Low block match_success | Heuristic weak? | Check which techs/metrics in bullets |
| Many false negatives | Validator rules mismatch? | Manual review of removed claims |
| Over-retention (low removal) | Validator too permissive? | Check for obvious invented claims |
| Wrong blocks matched | Heuristic choosing wrong prefix? | Inspect top_matched_blocks |

## Pre-Phase-5A: Improve CVAdaptationAgent

**Before running E2E tests**, enhance CVAdaptationAgent with "Google-style" bullet rules:

### Current Output (Weak)
```
- Contributed to reporting systems
- Helped with data analysis
- Involved in automation projects
```

### Google-Style Output (Strong)
```
- Built 10+ automated reporting pipelines reducing manual work from 5-6 hours to ~1 hour
- Analyzed installed base data across 61 customers, driving account prioritization
- Orchestrated multi-source data consolidation for 30-40 international stakeholders
```

### Implementation
In `CVAdaptationAgent`:
1. Active voice only (no "was involved in", "helped with")
2. Measurable impact + metric when frozen metric exists
3. Technology stack explicit
4. Emphasis matching positioning (e.g., "Automation Engineer" → highlight Make/n8n)
5. Drop filler words: "supported", "assisted", "worked on"

**Why**: Test a safe AND useful pipeline, not a paranoid one.

## Phase 5A Implementation

```python
# app/tests/test_cv_e2e.py

class CVE2ETestSuite:
    """End-to-end testing framework."""

    async def run_test_case(
        self,
        job_offer: str,
        expected_positioning: str,
        test_name: str,
    ) -> CVTestResult:
        """Run one E2E test: analyze → position → adapt → validate → render."""
        # 1. Analyze offer
        # 2. Select positioning
        # 3. Generate documents (CV, letter, mail)
        # 4. Collect metrics
        # 5. Return result

    def collect_metrics(
        self,
        cv_html: str,
        adaptation: dict,
        quality_result: AdaptationValidationResult,
        master_cv: dict,
    ) -> CVMetrics:
        """Extract metrics from generated CV."""
        # Count bullets before/after
        # Check block matches
        # Validate HTML
        # Return CVMetrics dataclass

    async def run_all_test_cases(self) -> CVE2EReport:
        """Run 5 test cases and generate summary report."""
        # Run each test
        # Aggregate metrics
        # Generate charts/tables
        # Return report

class CVMetrics:
    """Metrics for one CV."""
    pass_count: int
    rewrite_count: int
    remove_count: int
    removal_rate: float
    retention_rate: float
    qc_recommendation: str
    best_matched_blocks: Dict[str, int]
    false_negatives: List[str]  # Manual notes
    # ... (20+ fields)

class CVE2EReport:
    """Summary across all test cases."""
    results_by_family: Dict[str, CVTestResult]
    aggregate_metrics: Dict[str, float]
    diagnostics: Dict[str, str]
    pass_fail_status: str
```

## Phase 5B: Run Tests & Analyze

1. **Run 5 test cases** with real job offers
2. **Generate HTML CVs** and save to `/outputs/`
3. **Collect metrics** in JSON
4. **Manual review** for false negatives
5. **Generate report** with charts
6. **Diagnose failures** if any

## Phase 5C: Document Findings

Publish findings:
- Which job families match well
- Which blocks were most helpful
- Common reasons for removals
- False negative patterns
- Recommendations for optimization

## Next: Handlers & Monitoring

After Phase 5 passes:

1. **Telegram Handlers**
   - Route CV to user with QC recommendation
   - "ACCEPT: CV ready" vs "REVIEW: Check these claims" vs "REJECT: Incompatible role"

2. **Production Monitoring**
   - Log metrics per application
   - Track false negatives from user feedback
   - Alert if removal_rate spikes

3. **Continuous Improvement**
   - Users mark false negatives in Telegram
   - Feedback fed back to:
     - Atomic blocks (if gaps found)
     - CVAdaptationAgent (if poor selection)
     - Validator rules (if too strict)

---

**Status**: Ready to proceed to Phase 5A (CVAdaptationAgent improvements)  
**Owner**: Claude Code  
**Deadline**: EOD Phase 5
