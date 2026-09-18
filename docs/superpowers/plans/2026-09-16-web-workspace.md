# Web workspace implementation plan

**Goal:** Deliver a functional French web workspace exposing existing job application and radar capabilities.
**Architecture:** FastAPI API, existing SQLAlchemy/agents, static HTML/CSS/JS, explicit local bootstrap.
**Tech Stack:** Python, FastAPI, SQLAlchemy, semantic HTML, browser JavaScript, Playwright.

1. API adapter and tests: add app/web/api.py and tests/test_web_api.py. Write failing API behavior tests, run pytest, implement overview, collections/detail, saved applications, status, analysis/generation, documents, companies, profile and settings. Preserve existing Telegram code and Master CV. Auth dependency restricts access. Test validation, ownership, pagination and unavailable AI.
2. Frontend: add app/web/index.html, styles.css and app.js. Implement persistent navigation, real data loading, filtering, modal create, detail drawer, keyboard escape, empty/error/loading states, document download/preview and settings. No invented scores or contacts. Use matching API contract in spec.
3. Local runtime: remove import-time DB mutation, mount frontend; explicit local bootstrap imports repository archive only when requested and seeds existing profile. Add start script and docs. No remote database writes.
4. Verify: run API tests and applicable existing tests; run browser against real local database; exercise import, search, saved application, status, document empty state, missing AI, desktop/mobile, console. Review changes and document capabilities and limitations.
