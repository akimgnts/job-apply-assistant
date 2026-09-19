# Offer Signal Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce offer noise by adding deterministic match scoring, recency ranking, and actionable filters to the offers radar.

**Architecture:** Add a small scoring service that reads a `JobOffer` plus optional profile text and returns score, tier, role family, recency label, and reasons. Expose those fields from `/api/offers`, add query filters for signal tier and recency, and update the vanilla UI controls/table.

**Tech Stack:** FastAPI, SQLAlchemy, vanilla JS, pytest.

---

### Task 1: Deterministic scoring service
- Create `app/services/offer_signal_service.py`.
- Test role keywords, negative signals, recency, and tiers in `tests/test_offer_signal_service.py`.

### Task 2: API integration
- Modify `app/web/service.py` to add signal metadata in `offer_data`.
- Modify `app/web/api.py` to support `signal=priority|potential|noise|recent` and sort by signal score then freshness.
- Add tests in `tests/test_web_api.py`.

### Task 3: UI filters
- Modify `app/web/static/app.js` to add signal filter and show match score/tier/reasons.
- Run tests and verify API locally.
