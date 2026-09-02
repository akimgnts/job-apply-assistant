# GIT SAFETY — Job Market Radar Feature Branch

## Critical Rules

**Objective:** Isolate Job Market Radar MVP (Phases 1–5) from production `main` branch. Experiment freely on `feature/job-market-radar` without risking existing Telegram pipeline.

---

## Before Any Modification

1. **Verify clean working tree**
   ```bash
   git status
   ```
   All changes committed, nothing pending.

2. **Confirm you are on correct branch**
   ```bash
   git branch
   ```
   Should show: `* feature/job-market-radar`

3. **If not on feature branch, switch immediately**
   ```bash
   git checkout feature/job-market-radar
   ```

---

## During Development (Phases 1–5)

### Code Changes
- ✅ DO: Modify/create code only on `feature/job-market-radar`
- ✅ DO: Add new agents, services, templates
- ✅ DO: Modify existing services (extend, don't replace)
- ❌ DO NOT: Delete existing agents or services
- ❌ DO NOT: Modify Telegram handlers without explicit approval
- ❌ DO NOT: Change Master CV integration (Master V3.1 is locked)

### Database Schema
- ✅ DO: Create new migrations for new tables (companies, job_offers, company_contacts)
  ```bash
  alembic revision --autogenerate -m "Add job_offers, companies, company_contacts tables"
  ```
- ✅ DO: Review generated migration file before applying
- ✅ DO: Apply only to local database for testing
- ❌ DO NOT: Modify existing migrations
- ❌ DO NOT: Delete existing table columns
- ❌ DO NOT: Rename existing tables

### Git Commits
- **One commit per phase completion**
  ```bash
  git add .
  git commit -m "phase-1: add companies, job_offers, company_contacts tables + Alembic migrations"
  git commit -m "phase-2: implement URLScraperAgent with trafilatura extraction"
  git commit -m "phase-3: integrate AnalysisAgent, compute skill_evidence_map"
  git commit -m "phase-4: add company aggregation and skill_frequency computation"
  git commit -m "phase-5: real lead discovery (manual verification + source tracking)"
  git commit -m "phase-6: implement OutreachEmailAgent with Evidence Matrix + quality validation"
  ```

- **Format:** `phase-X: description`
- **Never:** Commit sensitive data (.env, keys, passwords)
- **Never:** Push directly to `main` or `master`

---

## Git Push Rules

- ✅ Push to `feature/job-market-radar` freely
  ```bash
  git push -u origin feature/job-market-radar
  ```

- ❌ NEVER push to `main` or `master` without explicit user approval
- ❌ NEVER force-push (`--force`, `--force-with-lease`)
- ❌ NEVER rebase against `main` without approval

---

## Integration with Main Pipeline

### Before Continuing Past Phase 5
- Stop implementation
- Run full test suite against current `main` (verify no regression)
- Generate report:
  ```bash
  git diff main...feature/job-market-radar > /tmp/radar-diff.patch
  git log main..feature/job-market-radar --oneline
  ```
- Document:
  - Files created/modified
  - Migrations added
  - Tests executed + results
  - Any regressions detected
  - Rollback procedure

### Rollback If Needed
If something breaks:
```bash
# Local: reset to last working commit
git reset --hard <commit-hash>

# Or: switch back to main
git checkout main
```

### Merge Only With Approval
- Feature branch will NOT merge to `main` automatically
- User must review report from Phase 5
- User must explicitly approve merge
- Merge process:
  ```bash
  git checkout main
  git pull origin main
  git merge --no-ff feature/job-market-radar
  git push origin main
  ```

---

## Safety Checklist Before Merge

- [ ] All phases 1–5 complete and tested
- [ ] No existing Telegram handlers modified
- [ ] No Master CV integration broken
- [ ] New migrations applied cleanly to fresh test DB
- [ ] No hardcoded credentials in code
- [ ] Evidence Matrix mapping tested (skill_evidence_map populated correctly)
- [ ] Phase 6 OutreachEmailAgent generates valid emails (no invented claims)
- [ ] All commits follow `phase-X: description` format
- [ ] No force-push history
- [ ] Working tree is clean (`git status` shows nothing pending)

---

## Emergency Procedures

### If Merge Conflicts Occur
```bash
git checkout feature/job-market-radar
git merge main  # May create conflicts
# Resolve conflicts manually, keeping NEW feature code
git add .
git commit -m "merge: resolve conflicts with main"
```

### If Main Changes During Feature Development
```bash
git fetch origin main
git log main..feature/job-market-radar --oneline  # See feature commits
# Feature code is isolated; only merge when ready
```

### If You Need to Discard All Feature Changes
```bash
git checkout main
git branch -D feature/job-market-radar
```

---

## Questions?

- Slack/email user if any rule violation risk
- Never assume it's OK to break isolation
- When in doubt, ask before committing

---

**Isolation is not a punishment; it's protection. Experiment fearlessly on this branch. Main stays safe.**
