# Skill Gap Intelligence V1

## Overview

The Skill Gap Intelligence system transforms the Job Apply Assistant from a simple CV generator into a **Career Intelligence Platform**.

Instead of just analyzing job offers one-by-one, the system now learns from every analyzed offer to progressively discover:

- Recurring missing skills (gaps)
- Most frequently requested technologies
- Strongest profile strengths
- Best matching role families
- Highest ROI portfolio projects

## Philosophy

### Before
```
Offer → Analysis → CV → Done
```

### After
```
Offer → Analysis → Gap Analysis → Store Learning Signals → Aggregate Insights → Career Intelligence
```

Every analyzed offer makes the system smarter.

## Architecture

### Core Components

#### 1. Skill Gap Event Storage (`SkillGapEvent`)
Captures individual skill gaps from each job analysis.

**Fields:**
- `skill_name` - Name of the skill
- `required` - Was skill required? (boolean)
- `present` - Does candidate have skill? (boolean)
- `gap` - Is this a gap? (required=true AND present=false)
- `importance_score` - 1-10 scale
- `confidence` - Confidence level 1-10
- `role_family` - Target role (Data Analyst, Data Engineer, etc.)
- `positioning` - Chosen angle for the role

#### 2. Aggregation Service (`SkillGapAggregationService`)
Analyzes skill gap events across all offers.

**Key Queries:**
```python
# Top requested skills across all offers
top_requested = get_top_requested_skills(db, user_id, limit=20)
# Returns: [{"skill": "SQL", "frequency": 82, "percentage": 82%}, ...]

# Most frequent missing skills
gaps = get_most_frequent_gaps(db, user_id, limit=20)
# Returns: [{"skill": "dbt", "frequency": 63, "percentage": 63%}, ...]

# Candidate's strongest skills
strengths = get_strongest_skills(db, user_id, limit=20)
# Returns: [{"skill": "Python", "frequency": 95, "percentage": 95%}, ...]

# Critical gaps by ROI
critical = calculate_critical_gaps(db, user_id, limit=20)
# Returns: [{"skill": "dbt", "critical_gap_score": 47.5}, ...]
```

#### 3. Capture Service (`SkillGapCaptureService`)
Extracts skills from job analysis and determines gaps.

**Skill Sources:**
- Required skills (importance: 9/10)
- Soft skills (importance: 7/10)
- ATS keywords (importance: 6/10)

**Gap Detection:**
Compares required skills against candidate's profile blocks.

#### 4. Project Recommendation Engine (`ProjectRecommendationEngine`)
Generates portfolio project recommendations to fill gaps.

**Built-in Projects:**
- Modern Data Stack Portfolio Project (solves: dbt, SQL, data modeling)
- Job Market Observatory - Airflow Pipeline (solves: airflow, orchestration)
- Cloud Deployment of Microservice (solves: AWS, Docker, Kubernetes)
- Real-time Analytics Dashboard (solves: Power BI, Tableau, visualization)
- Spark Data Processing Pipeline (solves: Spark, big data)
- Machine Learning Model in Production (solves: MLOps, model deployment)
- REST API Design & Documentation (solves: API design, REST, backend)
- Git Workflow & CI/CD Automation (solves: Git, CI/CD, testing)
- Data Quality & Testing Framework (solves: data quality, testing)
- Documentation & Knowledge Base (solves: technical writing, documentation)

**ROI Scoring:**
```
ROI = gaps_solved × impact_level × portfolio_value ÷ difficulty
```

#### 5. Career Intelligence Service (`CareerIntelligenceService`)
Main service providing complete career insights.

**Output Format:**
```python
{
    "total_offers_analyzed": 42,
    "strengths": [
        {"skill": "Python", "percentage": 95, "avg_importance": 8.2},
        ...
    ],
    "frequent_gaps": [
        {"skill": "dbt", "percentage": 63, "avg_importance": 7.5},
        ...
    ],
    "critical_gaps": [
        {"skill": "dbt", "critical_gap_score": 47.5},
        ...
    ],
    "recommended_projects": [
        {
            "rank": 1,
            "title": "Modern Data Stack Portfolio Project",
            "solved_gaps": ["dbt", "sql"],
            "impact": "high",
            "difficulty": "intermediate",
            "roi_score": 18.5
        },
        ...
    ],
    "best_matching_role_families": [
        {"role_family": "Data Analyst", "match_score": 87.5},
        ...
    ],
    "weakest_matching_role_families": [
        {"role_family": "Senior Data Engineer", "match_score": 42.3},
        ...
    ]
}
```

## Data Flow

### Analysis → Gap Capture

```
User submits offer
↓
AnalysisAgent.analyze() → analysis JSON
↓
PositioningAgent.choose_angle() → positioning + role_family
↓
SkillGapIntegrationService.capture_gaps_from_application()
    ↓ (calls)
SkillGapCaptureService.capture_gaps_from_analysis()
    ↓ (iterates through)
required_skills → create SkillGapEvent for each
soft_skills → create SkillGapEvent for each
ats_keywords → create SkillGapEvent for each
    ↓ (each event)
check candidate_skills → set present=true/false
record event → insert to database
↓
SkillGapEvent records stored
```

### Aggregation → Intelligence

```
User requests /intelligence
↓
CareerIntelligenceService.generate_intelligence_snapshot()
    ↓
SkillGapAggregationService.get_career_intelligence_summary()
    ├─ get_top_requested_skills()
    ├─ get_strongest_skills()
    ├─ get_most_frequent_gaps()
    ├─ calculate_critical_gaps()
    └─ get_role_family_strengths()
    ↓
ProjectRecommendationEngine.get_recommendations()
↓
Complete intelligence JSON
↓
CareerIntelligenceService._format_*() → format for Telegram
↓
User sees insights
```

## Telegram Commands

### Main Intelligence Commands

#### `/intelligence`
**Career Intelligence Summary** - Overview of strengths, gaps, and recommendations.

```
🧠 Career Intelligence Summary

📊 Offers Analyzed: 42

💪 Top Strengths:
  • Python (95%)
  • SQL (92%)
  • Pandas (88%)

⚠️ Frequent Gaps:
  • dbt (63%)
  • Airflow (58%)
  • AWS (41%)

🔴 Critical Gaps to Address:
  • dbt (score: 47.5)
  • Airflow (score: 39.2)
  • AWS (score: 28.1)
```

#### `/gaps`
**Detailed Skill Gaps Analysis** - All gaps ranked by frequency and importance.

```
🔍 Skill Gaps Analysis

Most Frequent Gaps:
1. dbt - 63% (importance: 8.2/10)
2. Airflow - 58% (importance: 7.9/10)
3. AWS - 41% (importance: 7.1/10)
...

Critical Gaps (by ROI):
1. dbt (score: 47.5)
2. Airflow (score: 39.2)
...
```

#### `/projects`
**Recommended Portfolio Projects** - Top projects ranked by gap coverage and ROI.

```
📋 Recommended Portfolio Projects

1. Modern Data Stack Portfolio Project
   Solves: dbt, sql, data-modeling
   Impact: high | Difficulty: intermediate
   Hours: 40 | ROI Score: 18.5

2. Job Market Observatory - Airflow Pipeline
   Solves: airflow, orchestration, automation
   Impact: high | Difficulty: intermediate
   Hours: 50 | ROI Score: 16.2
...
```

#### `/roles`
**Role Family Analysis** - Which roles match best/worst.

```
👔 Role Family Analysis

Best Matching Roles:
  • Data Analyst: 87.5% match
  • BI Analyst: 85.2% match
  • Analytics Engineer: 78.1% match

Need Most Development:
  • Senior Data Engineer: 42.3% match
  • Data Team Lead: 38.7% match
  • ML Engineer: 35.2% match
```

### Detailed Analysis Commands

#### `/top_skills`
Top 15 most frequently requested skills.

#### `/gaps_most`
Top 15 most frequent gaps.

#### `/strengths`
Top 15 strongest candidate skills.

#### `/save_intelligence`
Save current intelligence snapshot to database for historical tracking.

## Integration with Existing Pipeline

### Minimal Changes
Only 2 changes needed to enable skill gap capture:

1. **In handler `handle_offer()`** - Add one line after analysis:
```python
SkillGapIntegrationService.capture_gaps_from_application(
    db, user_id, app, analysis, positioning, role_family
)
```

2. **In handler `elevia_load_offer()`** - Add same line after analysis.

### Non-Breaking
- Skill gap capture is optional enrichment
- Fails gracefully if database unavailable
- Doesn't block main offer analysis
- Zero changes to AnalysisAgent, MatchingAgent, PositioningAgent

## Success Metrics

After 100+ analyzed offers, system can answer:

1. **What are my most common missing skills?**
   → `/gaps` shows frequency distribution

2. **What skills would increase my matching score the most?**
   → `/projects` shows high-ROI learning

3. **What portfolio projects should I build next?**
   → `/projects` ranked by ROI and coverage

4. **Which role families fit me best?**
   → `/roles` shows match scores

5. **Which role families require the biggest progression?**
   → `/roles` shows weakest matches

## Data Quality

### No Guessing
All insights are based on:
- ✅ Actual analyzed offers
- ✅ Actual detected gaps (required & not present)
- ✅ Actual observed frequencies
- ❌ No invented skills
- ❌ No predicted demand
- ❌ No AI guessing

### Skill Matching
Candidate skills sourced from:
- Profile block titles
- Profile block tags
- Profile block categories (skill, tool)

Skills are normalized (lowercased, trimmed) for reliable matching.

## Importance Scoring

Three tiers of importance:

| Source | Importance | Confidence | Reasoning |
|--------|-----------|-----------|-----------|
| Required Skills | 9/10 | 9/10 | High confidence, critical |
| Soft Skills | 7/10 | 8/10 | Medium confidence, valuable |
| ATS Keywords | 6/10 | 6/10 | Lower confidence, could be noise |

## Critical Gap Score

Formula:
```
gap_score = frequency × importance × confidence / 100

Examples:
dbt: 10 appearances × 9 importance × 9 confidence / 100 = 8.1
Airflow: 8 × 8 × 8 / 100 = 5.1
```

Higher scores indicate gaps with:
- High frequency (appears often)
- High importance (candidates care)
- High confidence (truly required)

## Project Matching

Projects are matched to gaps by:
1. Extract all critical gaps (top 15)
2. Normalize gap skill names
3. Check each project's `solves_gaps`
4. Count matches per project
5. Calculate ROI score
6. Rank by (ROI, gap_count)

## Historical Snapshots

Users can save intelligence snapshots with `/save_intelligence`.

Snapshots stored in `CareerIntelligenceSnapshot` table:
- Timestamp
- Total offers analyzed at that time
- Skills, gaps, projects at that time
- Role family scores at that time

Useful for:
- Tracking progress over time
- Comparing skill development
- Validating recommendations

## Design Constraints

### MVP Scope
✅ Storage of skill gap events
✅ Aggregation across offers
✅ Statistics and frequency analysis
✅ Project recommendations
✅ Career intelligence dashboard
✅ Role family analysis

### Explicitly Out of Scope
❌ Autonomous learning agents
❌ Self-modifying prompts
❌ Automatic retraining
❌ Offer recommendation agents
❌ AI-powered gap prediction

## Future Enhancements (V2+)

1. **Learning Optimization**
   - Prioritize projects by skill impact
   - Suggest learning order (prerequisites first)
   - Track actual skill acquisition

2. **Market Intelligence**
   - Regional demand analysis
   - Salary correlation with skills
   - Emerging tech trends

3. **Competitive Benchmarking**
   - Compare against similar role requirements
   - Industry standards
   - Peer performance

4. **Predictive Insights**
   - Project success likelihood
   - Time to mastery estimates
   - Job market fit predictions

5. **Personalized Recommendations**
   - Learning style preferences
   - Available time investment
   - Learning resource suggestions

## Database Schema

### SkillGapEvent
```
id | telegram_user_id | application_id | offer_title | company | 
role_family | positioning | skill_name | skill_category | 
required | present | gap | importance_score | confidence | created_at
```

Indexes:
- `(telegram_user_id)`
- `(application_id)`
- `(skill_name)`

### CareerIntelligenceSnapshot
```
id | telegram_user_id | total_offers_analyzed | 
top_strengths | frequent_gaps | critical_gaps | 
recommended_projects | role_family_strengths | 
role_family_weaknesses | created_at | updated_at
```

## Testing

### Unit Tests
```python
# Test skill extraction
assert extract_skills_from_analysis(analysis) == (required, soft, ats)

# Test gap detection
assert is_skill_present("Python", candidate_skills) == True

# Test aggregation
gaps = get_most_frequent_gaps(db, user_id)
assert gaps[0]["skill"] == "dbt"
```

### Integration Tests
```python
# End-to-end: offer → analysis → gaps → intelligence
offer_text = "..."
analysis = await AnalysisAgent.analyze(db, offer_text)
SkillGapIntegrationService.capture_gaps_from_application(...)
intelligence = CareerIntelligenceService.generate_intelligence_snapshot(...)
assert intelligence["total_offers_analyzed"] > 0
```

## Troubleshooting

### No gaps captured
→ Check that profile blocks have relevant skills/tags
→ Verify skill matching is case-insensitive
→ Check database migration applied

### Intelligence not available
→ Need at least 10 offers analyzed
→ Check SkillGapEvent count: `SELECT COUNT(*) FROM skill_gap_events WHERE telegram_user_id = ?`

### Wrong project recommendations
→ Check critical gaps are correctly ranked
→ Verify ProjectRecommendationEngine.PROJECTS has relevant skills

## Performance

- Capturing gaps: ~0.1s per offer (10 skill events avg)
- Aggregation: ~0.5s (queries distinct skills)
- Intelligence generation: ~1s (3 aggregation calls)

Optimize if needed with:
- Database indexes (already created)
- Materialized views for common queries
- Snapshot caching (CareerIntelligenceSnapshot)

## See Also

- `IMPLEMENTATION_NOTES.md` - Technical details
- `ELEVIA_INTEGRATION.md` - Job offer sourcing
- `CLAUDE.md` - Project guidelines
- `README.md` - User guide
