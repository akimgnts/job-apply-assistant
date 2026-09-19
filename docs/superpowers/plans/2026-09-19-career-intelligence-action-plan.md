# Career Intelligence Action Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn analyzed offers and skill gaps into a structured “Mon évolution” action dashboard.

**Architecture:** Keep the existing web app and database schema. Add a focused service that aggregates `JobAnalysis` and `SkillGapEvent` into market signals, gap priorities, and concrete learning actions, then expose it through `/api/intelligence` and render it in the existing page.

**Tech Stack:** FastAPI, SQLAlchemy, vanilla JS, pytest.

---

### Task 1: Add structured career intelligence service

**Files:**
- Create: `app/services/career_action_plan_service.py`
- Test: `tests/test_career_action_plan_service.py`

- [ ] Write tests for gap priorities from latest analyses and skill gap events.
- [ ] Implement aggregation with deterministic action recommendations.
- [ ] Run targeted tests.

### Task 2: Wire web API

**Files:**
- Modify: `app/web/api.py`
- Test: `tests/test_web_api.py`

- [ ] Write test asserting `/api/intelligence` returns `market_signals`, `gap_priorities`, and `action_plan`.
- [ ] Replace flat counter route logic with the new service.
- [ ] Run targeted tests.

### Task 3: Upgrade “Mon évolution” UI

**Files:**
- Modify: `app/web/static/app.js`
- Modify: `app/web/static/styles.css`

- [ ] Render market sample size, top requested skills, critical gaps, and action cards.
- [ ] Keep empty state for no analyses.
- [ ] Verify API health and test suite.
