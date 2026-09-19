# Gmail Candidate Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn imported Gmail messages into a usable candidate-tracking table for the last three weeks of real activity.

**Architecture:** Add a focused tracking agent service that classifies employment-related email events, extracts company/job/source signals, and groups messages into opportunity rows without mutating Gmail. Expose the grouped rows through the existing private tracking API and render them in the existing `Suivi & Gmail` page.

**Tech Stack:** FastAPI, SQLAlchemy, vanilla JS/CSS, pytest, SQLite-backed local workspace.

---

### Task 1: Email classification and extraction service

**Files:**
- Create: `app/services/application_tracking_agent.py`
- Test: `tests/test_application_tracking_agent.py`

- [ ] Write failing tests for employment labels, job-board detection, company extraction, and opportunity grouping.
- [ ] Run the new tests and verify failures reference missing module/functions.
- [ ] Implement minimal deterministic rules for labels: `cold_email`, `application_sent`, `application_ack`, `recruiter_reply`, `interview_or_test`, `rejection`, `job_board_alert`, `bounce`, `noise`.
- [ ] Run tests and keep existing Gmail tests green.

### Task 2: Tracking API opportunity endpoint

**Files:**
- Modify: `app/api/tracking.py`
- Test: `tests/test_tracking_api.py`

- [ ] Write failing API test for `/api/tracking/opportunities` returning grouped opportunity rows from imported Gmail events.
- [ ] Implement endpoint using `ApplicationTrackingAgent.build_opportunities`.
- [ ] Include counts, latest event, status, source, labels, and linked app id when known.
- [ ] Run tracking API tests.

### Task 3: Web table for real history

**Files:**
- Modify: `app/web/static/tracking.js`
- Modify: `app/web/static/styles.css`

- [ ] Replace the empty “Mes dossiers” default with a candidate history table from `/tracking/opportunities`.
- [ ] Keep existing message review drawer and dossier drawer intact.
- [ ] Add compact filters for all, needs review, replies, interviews, rejections, job boards, ignored/noise.
- [ ] Verify the page shows rows on the real local DB.

### Task 4: Backfill existing imported emails

**Files:**
- Runtime action only against local SQLite DB.

- [ ] Reclassify pending imported Gmail rows with the new deterministic agent.
- [ ] Preserve confirmed/processed rows and Gmail read-only behavior.
- [ ] Verify status counts and opportunity count.
- [ ] Restart local server and reload Chrome tab.

### Task 5: Final validation

**Files:**
- Test suites and local browser.

- [ ] Run focused tests: Gmail tracking, application tracking agent, tracking API.
- [ ] Check `git status`, commit code changes, push master.
- [ ] Verify Chrome shows the real tracker on `http://127.0.0.1:8769/#applications?view=tracking`.
