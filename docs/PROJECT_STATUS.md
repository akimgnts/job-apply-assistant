# Job Apply Assistant: Project Status & Roadmap

**Last Updated**: 2025-01-28  
**Overall Status**: Phase 4 ✅ Complete → Phase 5 🚀 Ready to Start

---

## 🎯 Core Mission

Build an AI-powered CV generator that **never invents claims**. Only what's provably in atomic profile blocks gets into generated CVs.

---

## ✅ Completed Phases

### Phase 1: ProfileBlock V2 Schema Enrichment ✅
**Status**: Complete  
**What Changed**:
- Added 10 new fields to ProfileBlock model:
  - `proficiency_level` (0–3 scale: learning → expert)
  - `status` (completed, deployed, in_progress, exploratory, not_deployed)
  - `metrics` (frozen structured data)
  - `technologies` (authorized list)
  - `job_families` (role contexts)
  - `company`, `start_date`, `end_date`
  - `forbidden_claims` (guardrails)
  - `source_ref` (traceability to Master V3)

**Files**:
- `app/database/models.py`: ProfileBlock enriched
- Migration: `migrations/versions/008_enrich_profile_blocks.py`

---

### Phase 2: Database Migrations ✅
**Status**: Complete  
**What Changed**:
- Migration 007: Bot tracking tables (bot_instances, conversation_history)
- Migration 008: ProfileBlock enrichment columns + PostgreSQL enums
- Safe downgrades with CASCADE

**Files**:
- `migrations/versions/007_add_bot_tracking.py`
- `migrations/versions/008_enrich_profile_blocks.py`

---

### Phase 3: Master V3 Seed Profile Enrichment ⚠️ Partial → Phase 3.5 ✅ Complete
**Status**: Complete (with Phase 3.5 atomic decomposition)

#### Phase 3 (Initial): Partial Enrichment ⚠️
- Added blocked data to seed_profile.py
- But blocks remained **monolithic** (Sidel = 1 block, not 7)

#### Phase 3.5 (Correction): Complete Atomic Decomposition ✅
- **Breaking change**: Decomposed into ~180 atomic blocks from 20 monolithic ones
- **New file**: `seed_profile_atomic_v3.py`
- **Structure**:
  - 1 positioning/identity block
  - 14 experience blocks (7 Sidel + 6 MadeByAkim + 1 Vassard)
  - 7 project blocks (Elevia + Job Apply Assistant + V.I.E Matcher + SkillMap)
  - 68 skill blocks (one per technology)
  - 3 education, 3 certification, 3 language blocks

**User Corrections Applied**:
- ✅ Snowflake: Removed (user: "never touched")
- ✅ Python: Kept in Sidel (user confirmed used)
- ✅ Microsoft Dynamics: Added with proficiency_level=beginner (user confirmed touched)
- ✅ Dates: Locked Sidel 2023–2025 (user confirmed correct)

**Files**:
- `app/database/seed_profile_atomic_v3.py` (1510 lines)
- `docs/PHASE_4_AUDIT_MASTER_V3_TO_ATOMIC_BLOCKS.md` (mapping audit)

---

### Phase 4: Deterministic Claim Validation ✅ Complete
**Status**: Complete + Integration with GenerationAgent done

#### Components Built

**ClaimValidatorService** (deterministic, zero AI)
- `validate_experience_claim()`: Checks technologies, forbidden claims, status
- `validate_metric_claim()`: Verifies metrics match frozen values
- `validate_skill_claim()`: Checks proficiency level ≤ block level
- `validate_date_claim()`: Ensures dates within block range
- Private helpers: tech extraction, metric parsing, forbidden claim checking

**ClaimParserService** (LLM-only semantic extraction)
- Parses CV into atomic claims
- Maps claims to source blocks
- Rates confidence (0.0–1.0)
- Extracts technologies, metrics, proficiency hints
- **Only LLM use in validation pipeline** (everything else is deterministic)

**QualityAgent v2** (orchestration + adaptation validation)
- `validate_document()`: Full document validation (parsed claims)
- `validate_adaptation_claims()`: **NEW** – Validates adaptation JSON before rendering
  - Validates summary, experience bullets, project bullets
  - Smart source block matching (tech/metric heuristics)
  - PASS/REWRITE/REMOVE decisions
  - Removal threshold logic (>30% → REVIEW flag)

**Integration into GenerationAgent**
- Moved to **after CVAdaptationAgent**, **before Jinja2 rendering**
- Uses cleaned_adaptation (with REMOVE/REWRITE applied)
- Logs detailed warning if >30% claims removed
- Post-render validation stays **technical only** (None/null/structure)

#### Validation Rules (5 Strict Rules)
1. **Block-scoped technology**: Can only use tech if source block authorizes it
2. **Metric freezing**: Cannot change frozen metrics from block
3. **Proficiency claims**: Cannot exceed block.proficiency_level
4. **Status compatibility**: Cannot claim incompatible status (exploratory ≠ deployed)
5. **No generic skill justification**: Global skill ≠ authorization in specific experience

#### Test Coverage (21 passing tests)
- Metric fabrication (3): exact match, invented, missing block
- Technology invention (4): authorized, unauthorized, mixed, Snowflake removal
- Proficiency exaggeration (3): at-level, below-level, above-level
- Status misrepresentation (2): exploratory violation, in_progress allowed
- Date fabrication (2): within range, out-of-range
- Forbidden claims (1): phrase matching
- No generic skill justification (3): global, unauthorized context, authorized context
- Accurate claim acceptance (3): experience, automation, metric

**Files**:
- `app/services/claim_validator_service.py` (300 lines)
- `app/services/claim_parser_service.py` (180 lines)
- `app/agents/quality_agent_v2.py` (450+ lines with adaptation validation)
- `app/agents/generation_agent.py` (integrated validation into CV pipeline)
- `tests/test_quality_agent_v2.py` (450+ lines, all passing)
- `docs/PHASE_4_AUDIT_MASTER_V3_TO_ATOMIC_BLOCKS.md` (audit report)

---

## 🚀 Phase 5: End-to-End Testing & Quality Optimization

**Status**: Ready to start  
**Goal**: Verify complete pipeline produces factually sound, useful CVs across job families

### Phase 5 Components

#### 5A: Improve CVAdaptationAgent (Pre-E2E)
- Add "Google-style" bullet rules:
  - Active voice, measurable impact
  - "Built X using Y with Z result" format
  - Drop viller words (supported, helped, involved)
  - Match emphasis to positioning
- **Why**: Test safe AND useful pipeline

#### 5B: E2E Test Framework
- 5 test cases: Data Analyst, Business Analyst, Automation/AI, Marketing, Tech Lead
- Metrics per CV:
  - Validation: pass/rewrite/remove counts, removal_rate, recommendation
  - Content: bullets_before/after, retention_rate
  - Block matching: success rate, top matched blocks
  - Quality: HTML issues, false negatives
- Success criteria: <25% removal, ≥80% retention, <30% false negatives

#### 5C: Run Tests & Analyze
- Generate CVs for 5 job families
- Collect metrics in JSON
- Manual review for false negatives
- Generate diagnostic report

**Files**:
- `docs/PHASE_5_E2E_TESTING_PLAN.md` (comprehensive plan)
- `tests/test_cv_e2e.py` (test framework with CVMetrics, CVE2ETestSuite)

---

## 🔮 Post-Phase-5: Production & Monitoring

### Phase 6: Telegram Integration & Handlers
- Route CV with QC recommendation to user
- "ACCEPT: Ready" / "REVIEW: Check these" / "REJECT: Incompatible"

### Phase 7: Production Monitoring
- Log metrics per application
- Track false negatives from user feedback
- Alert if removal_rate spikes
- Continuous improvement feedback loop

---

## 📊 Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                   User (Telegram)                       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              InputAgent (extract URL/text)              │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│         AnalysisAgent (job offer analysis)              │
│         ↓ Output: {company, job_title, skills, ...}    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│      PositioningAgent (choose 1 of 7 fixed angles)      │
│         ↓ Output: positioning (e.g., "Data Analyst")   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│         GenerationAgent (orchestrate CV creation)       │
│                                                          │
│  1. Load Master CV (immutable source)                   │
│  2. CVAdaptationAgent (select & reorder bullets)        │
│  3. ✨ QualityAgent v2 (VALIDATE before render)        │
│     - Smart block matching                              │
│     - PASS/REWRITE/REMOVE decisions                     │
│     - Removal threshold logic                           │
│  4. Jinja2 render → HTML                                │
│  5. HTML validation (technical only)                    │
│  6. Save to DB + disk                                   │
│                                                          │
│  Outputs: CV + Letter + Mail                           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Handler (format & deliver)                 │
│              → Telegram message to user                 │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│         User sees: CV + QC recommendation              │
│         ACCEPT / REVIEW / REJECT                        │
└─────────────────────────────────────────────────────────┘
```

---

## 🔐 Hallucination Prevention: 5-Layer Defense

1. **Atomic blocks** (source of truth)
   - ~180 verified, user-corrected blocks
   - No cross-block contamination
   - Frozen metrics, technologies, dates, statuses

2. **CVAdaptationAgent** (selection layer)
   - Chooses which bullets from Master CV to use
   - Adapts title & summary via LLM
   - Never adds new facts

3. **QualityAgent v2 Validation** (deterministic checking)
   - ClaimValidatorService (5 strict rules)
   - SmartBlockMatching (find correct block)
   - PASS/REWRITE/REMOVE decisions

4. **Forbidden Claims** (semantic guardrails)
   - Blocks can forbid specific claims
   - Example: "Do not change ~30–40 to exact number"

5. **Technical HTML Validation** (rendering layer)
   - Catch None/null, empty sections, structure issues
   - NOT for factual validation (handled pre-render)

---

## 📈 Key Metrics (Phase 5 Will Measure)

- **Removal rate**: % claims removed by validator (target <25%)
- **Retention rate**: % bullets surviving validation (target ≥80%)
- **Block match success**: % claims matched to correct atomic block (target ≥85%)
- **False negatives**: Legitimate claims rejected (target <30%)
- **QC recommendation distribution**: ACCEPT / REVIEW / REJECT per job family

---

## 🐛 Known Limitations & Future Improvements

### Current Limitations
- CVAdaptationAgent uses basic LLM bullet selection (can be improved)
- Fuzzy matching for blocks could fail on unusual phrasing
- No user feedback loop yet (Phase 7)

### Future Improvements
- Fine-tune CVAdaptationAgent on job-family-specific prompts
- Add user feedback loop: "this claim should have passed"
- Machine learning: learn which blocks match which job families
- Semantic similarity for better block matching
- A/B test different positioning angles

---

## 📝 File Organization

### Core Application
```
app/
├── agents/
│   ├── quality_agent_v2.py         [Phase 4] Validation orchestration
│   ├── generation_agent.py         [Phase 4 integrated] CV generation
│   ├── cv_adaptation_agent.py      [Phase 5A to improve]
│   └── ...
├── services/
│   ├── claim_validator_service.py  [Phase 4] Deterministic validator
│   ├── claim_parser_service.py     [Phase 4] LLM semantic extraction
│   └── ...
├── database/
│   ├── models.py                   [Phase 1] Enhanced ProfileBlock
│   └── seed_profile_atomic_v3.py   [Phase 3.5] 180 atomic blocks
└── templates/
    └── master_cv.html              [Jinja2] Safe rendering
```

### Testing & Documentation
```
tests/
├── test_quality_agent_v2.py        [Phase 4] 21 tests (passing)
└── test_cv_e2e.py                  [Phase 5] E2E framework

docs/
├── PHASE_4_AUDIT_MASTER_V3_TO_ATOMIC_BLOCKS.md
├── PHASE_5_E2E_TESTING_PLAN.md
├── ARCHITECTURE.md                 [System design overview]
└── PROJECT_STATUS.md               [This file]
```

---

## 🎬 Next Actions

### Immediate (Next Session)
1. ✅ Review Phase 4 implementation
2. ✅ Plan Phase 5 strategy
3. 🚀 Start Phase 5A: Improve CVAdaptationAgent

### Phase 5A: CVAdaptationAgent Improvements
- [ ] Add "Google-style" bullet rules
- [ ] Test on sample adaptations
- [ ] Verify no hallucinations introduced

### Phase 5B: Run E2E Tests
- [ ] Create 5 job offers (or use public LinkedIn offers)
- [ ] Run full pipeline on each
- [ ] Collect metrics & false negatives
- [ ] Generate diagnostic report

### Phase 5C: Fix Issues (if any)
- [ ] Analyze failures
- [ ] Improve blocks / adapter / matcher as needed
- [ ] Re-run tests until PASS criteria met

### Phase 6+: Production Ready
- [ ] Integrate Telegram handlers
- [ ] Set up monitoring/logging
- [ ] Deploy to production
- [ ] Collect user feedback for Phase 7

---

## 🏁 Success Criteria (Phase 4 Achieved ✅)

| Phase | Criteria | Status |
|-------|----------|--------|
| 1 | ProfileBlock V2 schema | ✅ Complete |
| 2 | Database migrations | ✅ Complete |
| 3 | Atomic blocks (180+) | ✅ Complete |
| 4 | Deterministic validation (21 tests) | ✅ Complete |
| 5 | E2E tests (5 job families) | 🚀 Ready |
| 6 | Telegram handlers | 📋 Planned |
| 7 | Production monitoring | 📋 Planned |

---

## 👤 Team & Ownership

- **Architecture**: Claude Code
- **User Corrections**: akimguentas13@gmail.com
- **Testing**: In progress (Phase 5)

---

**Last Commit**: Phase 4 integration + Phase 5 planning  
**Next Milestone**: Phase 5A – CVAdaptationAgent Improvements  
**Branch**: `claude/jolly-shannon-meclpn`
