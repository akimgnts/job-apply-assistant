# Skill Gap Intelligence Integration Guide

## Quick Start

The Skill Gap Intelligence system is **opt-in** and **non-breaking**. It works automatically alongside the existing CV generation pipeline.

### Step 1: Database Migration

Run the new migration to create skill gap tables:

```bash
# From project root
python -m alembic upgrade head
# or if using alembic directly
alembic upgrade head
```

This creates:
- `skill_gap_events` table
- `career_intelligence_snapshots` table
- Three indexes for performance

### Step 2: Enable Skill Gap Capture (Optional)

To automatically capture skill gaps from each analyzed offer, add this to the `handle_offer()` handler in `app/bot/handlers.py`:

**Location:** After `positioning_result` is obtained (around line 132)

```python
# After this line:
positioning_result = await PositioningAgent.choose_angle(analysis)

# Add this:
from app.services.skill_gap_integration_service import SkillGapIntegrationService

positioning = positioning_result.get("positioning", "Data Analyst BI")
skill_profile = positioning_result.get("skill_profile", "general_business_data")
role_family = positioning_result.get("role_family", positioning)

# Capture skill gaps (optional enrichment, non-blocking)
SkillGapIntegrationService.capture_gaps_from_application(
    db=db,
    telegram_user_id=user_id,
    application=app,
    analysis=analysis,
    positioning=positioning,
    role_family=role_family,
)
```

Same pattern for `elevia_load_offer()` if Elevia enabled.

### Step 3: Start Using Intelligence Commands

Once you've analyzed 10+ offers, new commands become available:

```
/intelligence   - Career intelligence summary
/gaps           - Detailed gap analysis
/projects       - Recommended portfolio projects
/roles          - Role family analysis
/top_skills     - Top 15 requested skills
/gaps_most      - Top 15 most frequent gaps
/strengths      - Top 15 candidate strengths
/save_intelligence - Save snapshot to database
```

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│ Telegram User                                            │
│ /intelligence /gaps /projects /roles                     │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ Career Intelligence Service                              │
│ - generate_intelligence_snapshot()                       │
│ - save_snapshot()                                        │
│ - get_intelligence_for_telegram()                        │
└────────────────┬────────────────────────────────────────┘
                 │
         ┌───────┴────────┬──────────────┐
         │                │              │
┌────────▼────────┐  ┌────▼──────┐ ┌────▼──────────┐
│ Aggregation     │  │ Projects   │ │ Role Analysis │
│ Service         │  │ Engine     │ │               │
│                 │  │            │ │               │
│ get_top_*()     │  │ get_        │ │ get_role_     │
│ get_most_*()    │  │ recommend() │ │ family_*()    │
│ calculate_*()   │  │            │ │               │
└────────┬────────┘  └────┬───────┘ └────┬──────────┘
         │                │              │
         └────────────────┼──────────────┘
                  │
         ┌────────▼─────────────┐
         │ SkillGapEvent Query  │
         │ (SQL GROUP BY, etc)  │
         └────────┬─────────────┘
                  │
         ┌────────▼─────────────┐
         │ PostgreSQL           │
         │ skill_gap_events     │
         │ (50K+ events/year)   │
         └──────────────────────┘

    CAPTURE SIDE (during /analyze):

┌────────────────────────────────┐
│ User: /submit job offer        │
└────────────────┬───────────────┘
                 │
         ┌───────▼────────┐
         │ InputAgent     │
         │ JobIngestion   │
         └───────┬────────┘
                 │
         ┌───────▼──────────┐
         │ AnalysisAgent    │
         │ (existing)       │
         └───────┬──────────┘
                 │
         ┌───────▼──────────┐
         │ PositioningAgent │
         │ (existing)       │
         └───────┬──────────┘
                 │
         ┌───────▼────────────────────────┐
         │ SkillGapIntegrationService     │
         │ (NEW: call capture_gaps)       │
         └───────┬────────────────────────┘
                 │
         ┌───────▼──────────────────────┐
         │ SkillGapCaptureService       │
         │ - extract required skills    │
         │ - extract soft skills        │
         │ - extract ATS keywords       │
         │ - check candidate_skills     │
         │ - record gap events          │
         └───────┬──────────────────────┘
                 │
         ┌───────▼──────────────────────┐
         │ INSERT SkillGapEvent         │
         │ (to database)                │
         └──────────────────────────────┘
```

## Integration Checklist

- [ ] Run database migration (`alembic upgrade head`)
- [ ] Verify tables created: `\dt skill_gap_events career_intelligence_snapshots`
- [ ] Add capture call to `handle_offer()` handler
- [ ] Add capture call to `elevia_load_offer()` handler (if Elevia enabled)
- [ ] Test with `/intelligence` after 10+ offers analyzed
- [ ] Monitor: `SELECT COUNT(*) FROM skill_gap_events`

## Non-Breaking Changes

The skill gap system is designed to be completely optional:

### If disabled:
- No capture calls executed
- No SkillGapEvent records created
- Intelligence commands return "not enough data"
- Existing CV generation unaffected

### If capture fails:
- Exception caught and logged
- Main offer analysis continues
- CV/letter generation still works
- User never sees gap capture failure

### Benefits:
- Can test with small user subset
- Easy to enable/disable
- No risk to existing functionality
- Gradual rollout possible

## Data Collection Timeline

After deployment, expect:

| Timeframe | Offers | Events | Intelligence |
|-----------|--------|--------|--------------|
| Week 1 | 5-10 | 75-150 | Sparse data |
| Month 1 | 20-40 | 300-600 | Useful patterns |
| Month 3 | 60-100 | 900-1500 | Strong insights |
| Month 6 | 120-200 | 1800-3000 | Strategic value |

**Threshold for usefulness:** ~100+ events (7-10 offers)

## API Reference

### SkillGapAggregationService

```python
from app.services.skill_gap_aggregation_service import SkillGapAggregationService
from sqlalchemy.orm import Session

# Top requested skills
skills = SkillGapAggregationService.get_top_requested_skills(
    db=db,
    telegram_user_id="123456",
    days=365,  # time range
    limit=20   # top N
)
# Returns: [{"skill": "SQL", "frequency": 82, "percentage": 82%, ...}, ...]

# Most frequent gaps
gaps = SkillGapAggregationService.get_most_frequent_gaps(
    db=db,
    telegram_user_id="123456",
    days=365,
    limit=20
)

# Candidate strengths
strengths = SkillGapAggregationService.get_strongest_skills(
    db=db,
    telegram_user_id="123456",
    days=365,
    limit=20
)

# Critical gaps (ranked by ROI)
critical = SkillGapAggregationService.calculate_critical_gaps(
    db=db,
    telegram_user_id="123456",
    days=365,
    limit=20
)

# Role family analysis
roles = SkillGapAggregationService.get_role_family_strengths(
    db=db,
    telegram_user_id="123456",
    days=365
)
# Returns: {
#     "Data Analyst": {"match_score": 87.5, "skills_present": 15, ...},
#     "Data Engineer": {"match_score": 62.3, "skills_present": 9, ...},
# }

# Complete intelligence in one call
intel = SkillGapAggregationService.get_career_intelligence_summary(
    db=db,
    telegram_user_id="123456",
    days=365
)
```

### CareerIntelligenceService

```python
from app.services.career_intelligence_service import CareerIntelligenceService

# Generate live intelligence
intel = CareerIntelligenceService.generate_intelligence_snapshot(
    db=db,
    telegram_user_id="123456",
    days=365
)

# Save snapshot for history
snapshot = CareerIntelligenceService.save_snapshot(
    db=db,
    telegram_user_id="123456",
    intelligence=intel
)

# Get latest saved snapshot
latest = CareerIntelligenceService.get_latest_snapshot(
    db=db,
    telegram_user_id="123456"
)

# Format for Telegram
message = CareerIntelligenceService.get_intelligence_for_telegram(
    db=db,
    telegram_user_id="123456",
    section="summary"  # or "gaps", "projects", "roles"
)
```

### SkillGapIntegrationService

```python
from app.services.skill_gap_integration_service import SkillGapIntegrationService
from app.database.models import Application

# Capture gaps from an analyzed application
success = SkillGapIntegrationService.capture_gaps_from_application(
    db=db,
    telegram_user_id=user_id,
    application=app,  # Application object
    analysis=analysis,  # Analysis JSON
    positioning=positioning,  # String
    role_family=role_family  # String (optional)
)

# Get capture status
status = SkillGapIntegrationService.get_capture_status(
    db=db,
    telegram_user_id="123456"
)
# Returns: {
#     "total_events": 1250,
#     "total_offers": 42,
#     "avg_events_per_offer": 29.8,
#     "ready_for_intelligence": True
# }
```

### ProjectRecommendationEngine

```python
from app.services.project_recommendation_engine import ProjectRecommendationEngine

# Get recommended projects
projects = ProjectRecommendationEngine.get_recommendations(
    db=db,
    telegram_user_id="123456",
    limit=5
)
# Returns: [
#     {
#         "rank": 1,
#         "title": "Modern Data Stack Portfolio Project",
#         "solved_gaps": ["dbt", "sql"],
#         "impact": "high",
#         "roi_score": 18.5,
#         ...
#     },
#     ...
# ]

# Get specific project details
project = ProjectRecommendationEngine.get_project_by_title(
    "Modern Data Stack Portfolio Project"
)
```

## Monitoring & Debugging

### Check capture is working

```sql
-- Count skill gap events
SELECT COUNT(*) FROM skill_gap_events;

-- By user
SELECT telegram_user_id, COUNT(*) as event_count 
FROM skill_gap_events 
GROUP BY telegram_user_id 
ORDER BY event_count DESC;

-- By skill
SELECT skill_name, COUNT(*) as frequency 
FROM skill_gap_events 
WHERE telegram_user_id = '123456'
GROUP BY skill_name 
ORDER BY frequency DESC;

-- Gaps (required & not present)
SELECT skill_name, COUNT(*) as gap_count 
FROM skill_gap_events 
WHERE telegram_user_id = '123456' AND gap = 1 
GROUP BY skill_name 
ORDER BY gap_count DESC;
```

### Check intelligence readiness

```python
from app.services.skill_gap_integration_service import SkillGapIntegrationService

status = SkillGapIntegrationService.get_capture_status(db, user_id)
print(f"Events: {status['total_events']}")
print(f"Offers: {status['total_offers']}")
print(f"Ready: {status['ready_for_intelligence']}")
```

### View intelligence snapshot

```python
from app.services.career_intelligence_service import CareerIntelligenceService

intel = CareerIntelligenceService.generate_intelligence_snapshot(db, user_id)
print(f"Offers analyzed: {intel['total_offers_analyzed']}")
print(f"Top gaps: {intel['critical_gaps'][:3]}")
print(f"Recommended projects: {intel['recommended_projects'][:3]}")
```

## Production Deployment

### Before deploying:

1. **Test locally**
   ```bash
   python -m alembic upgrade head
   # Analyze 10+ offers
   /intelligence  # Should show summary
   ```

2. **Verify on staging**
   - Run all 8 new commands
   - Check database queries are fast
   - Monitor error logs

3. **Gradual rollout**
   - Enable for 10% of users first
   - Monitor error rates
   - Check database growth
   - Scale to 100%

### Monitoring in production:

```bash
# Check error logs for skill gap capture
grep "SkillGapIntegrationService" /var/log/app.log
grep "SkillGapCaptureService" /var/log/app.log

# Monitor query performance
\timing on  -- in psql
SELECT COUNT(*) FROM skill_gap_events;  -- should be <10ms

# Check database size
SELECT pg_size_pretty(pg_total_relation_size('skill_gap_events'));
```

## Troubleshooting

### "No data" for intelligence commands
→ Need at least 10 offers analyzed
→ Check: `SELECT COUNT(DISTINCT application_id) FROM skill_gap_events WHERE telegram_user_id = ?`

### Skills showing as gaps that candidate has
→ Skill not in profile blocks or tags
→ Update profile blocks to include the skill

### Project recommendations not matching gaps
→ Check critical gaps: `/gaps` command
→ Verify ProjectRecommendationEngine.PROJECTS has matching skills

### Database is growing too fast
→ Expected: ~30 bytes per event
→ 100 offers = ~45KB
→ 1000 offers = ~450KB (very manageable)
→ If concerned, implement archive strategy

## Success Indicators

After 1 month with 30+ offers:

✅ `/intelligence` returns meaningful summary
✅ `/gaps` shows clear pattern of missing skills
✅ `/projects` recommends relevant portfolio projects
✅ `/roles` correctly identifies best/worst role fits
✅ Database queries complete in <1s
✅ No errors in logs

## Related Documentation

- `docs/SKILL_GAP_INTELLIGENCE.md` - Complete user guide
- `SKILL_GAP_INTELLIGENCE_NOTES.md` - Implementation details
- `CLAUDE.md` - Project guidelines
- `README.md` - User documentation

## Support

For questions or issues with skill gap intelligence integration:

1. Check logs: `grep -i skill_gap /var/log/app.log`
2. Verify database: `SELECT COUNT(*) FROM skill_gap_events`
3. Check documentation: `docs/SKILL_GAP_INTELLIGENCE.md`
4. Review code: `app/services/career_intelligence_service.py`
