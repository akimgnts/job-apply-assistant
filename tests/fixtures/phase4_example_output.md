# Phase 4 Company Intelligence Example

**FIXTURE-BASED DEMONSTRATION DATA**

This fixture demonstrates realistic Phase 4 output structure using the Sidel example and fictional companies (TechCorp, Enterprise A, DataCorp, StartupXYZ). 

**These companies are NOT production Radar results.** They are demonstration data showing how Phase 4 ranking works. Production results would reflect actual JobOffers + JobAnalyses in the database.

## Data Setup

### Company 1: Sidel

- **Total Active Offers**: 5
- **Relevant Offers** (Data/BI/AI): 5
- **Offers with Strong Profile Match** (fit >= 0.7): 3

#### Offers:

1. **Data Analyst** (Posted: 2026-09-01)
   - Required Skills: Python, SQL, Power BI, Excel
   - Skill Evidence:
     - Python: SKILL.PYTHON (DIRECT) + SIDEL.DATA_BI.001 (DIRECT) → **1.0 fit**
     - SQL: SKILL.SQL (DIRECT) → **1.0 fit**
     - Power BI: SKILL.BI (SUPPORTING) → **0.6 fit**
     - Excel: PROJECT.EXCEL_AUTOMATION.001 (DIRECT) → **1.0 fit**
   - **Offer Fit: (1.0 + 1.0 + 0.6 + 1.0) / 4 = 0.90**

2. **Business Intelligence Specialist** (Posted: 2026-09-02)
   - Required Skills: Power BI, DAX, SQL, Python
   - Skill Evidence:
     - Power BI: SKILL.BI (DIRECT) → **1.0 fit**
     - DAX: SKILL.DAX (DIRECT) → **1.0 fit**
     - SQL: SKILL.SQL (DIRECT) → **1.0 fit**
     - Python: SKILL.PYTHON (DIRECT) → **1.0 fit**
   - **Offer Fit: 1.0**

3. **Data Engineer** (Posted: 2026-08-30)
   - Required Skills: Python, Spark, Kafka, SQL, Cloud
   - Skill Evidence:
     - Python: SKILL.PYTHON (DIRECT) → **1.0 fit**
     - Spark: [] (GAP) → **0.0 fit**
     - Kafka: [] (GAP) → **0.0 fit**
     - SQL: SKILL.SQL (DIRECT) → **1.0 fit**
     - Cloud: SIDEL.AWS_DEPLOYMENT.001 (SUPPORTING) → **0.6 fit**
   - **Offer Fit: (1.0 + 0.0 + 0.0 + 1.0 + 0.6) / 5 = 0.52**

4. **Analytics Engineer** (Posted: 2026-09-03)
   - Required Skills: SQL, dbt, Python, Analytics
   - Skill Evidence:
     - SQL: SKILL.SQL (DIRECT) → **1.0 fit**
     - dbt: [] (GAP) → **0.0 fit**
     - Python: SKILL.PYTHON (DIRECT) → **1.0 fit**
     - Analytics: MADEBYAKIM.ANALYTICS.001 (DIRECT) → **1.0 fit**
   - **Offer Fit: (1.0 + 0.0 + 1.0 + 1.0) / 4 = 0.75**

5. **Python Developer (Data)** (Posted: 2026-08-28)
   - Required Skills: Python, NumPy, Pandas, Visualization
   - Skill Evidence:
     - Python: SKILL.PYTHON (DIRECT) → **1.0 fit**
     - NumPy: SIDEL.DATA_BI.002 (DIRECT) → **1.0 fit**
     - Pandas: SIDEL.DATA_BI.002 (DIRECT) → **1.0 fit**
     - Visualization: SKILL.BI (SUPPORTING) → **0.6 fit**
   - **Offer Fit: (1.0 + 1.0 + 1.0 + 0.6) / 4 = 0.90**

#### Skill Frequency Aggregation:

- Python: 5x
- SQL: 4x
- Power BI: 2x
- Excel: 1x
- Spark: 1x (GAP)
- Kafka: 1x (GAP)
- dbt: 1x (GAP)

#### Fit Aggregation:

- Average fit: (0.90 + 1.0 + 0.52 + 0.75 + 0.90) / 5 = **0.81**
- Best fit: **1.0** (BI Specialist offer)
- Strong matches (fit >= 0.7): **3 offers** (Data Analyst, BI Specialist, Python Dev)

#### Recruitment Intensity:

- Total offers: 5 active
- Relevant offers: 5
- **Intensity: HIGH** (6+ offers threshold met, 3+ relevant met)

#### Priority Score Calculation:

```
Components:
- Fit base: 0.81 × 40 = 32.4 points
- Offer volume: min(5 × 10, 30) = 30 points (capped)
- Best fit bonus: (1.0 - 0.6) × 20 = 8 points
- Intensity bonus (HIGH): 10 points

Total Score: 32.4 + 30 + 8 + 10 = 80.4 → 80 (rounded)
```

#### Priority Reasons:

1. "5 relevant offer(s)"
2. "Strong profile fit (81%)"
3. "3 offer(s) with strong verified evidence"
4. "High recent hiring intensity"
5. "Key skills: Python 5x · SQL 4x · Power BI 2x · Excel 1x"

---

### Company 2: TechCorp (Hypothetical)

- **Total Active Offers**: 8
- **Relevant Offers** (Data/BI/AI): 6
- **Offers with Strong Profile Match**: 2

#### Offers (Summary):

1. Data Analyst — fit: 0.65
2. Machine Learning Specialist — fit: 0.58
3. Analytics Manager — fit: 0.72
4. Data Science Lead — fit: 0.45
5. Business Analyst — fit: 0.51
6. BI Developer — fit: 0.78
7. ETL Engineer — fit: 0.42
8. Data Governance Specialist — fit: 0.38

#### Skill Frequency:

- Python: 6x
- SQL: 5x
- Machine Learning: 4x
- Spark: 3x (2x DIRECT, 1x SUPPORTING)
- AWS: 2x (all SUPPORTING)

#### Recruitment Intensity:

- Total: 8 active
- Relevant: 6
- **Intensity: HIGH**

#### Priority Score:

```
- Fit base: 0.58 × 40 ≈ 23 points
- Offer volume: min(6 × 10, 30) = 30 points
- Best fit bonus: (0.78 - 0.6) × 20 = 3.6 points
- Intensity bonus (HIGH): 10 points

Total: 66.6 → 67
```

#### Priority Reasons:

1. "6 relevant offer(s)"
2. "Moderate profile fit (58%)"
3. "2 offer(s) with strong verified evidence"
4. "High recent hiring intensity"
5. "Key skills: Python 6x · SQL 5x · Machine Learning 4x"

---

### Company 3: StartupXYZ

- **Total Active Offers**: 2
- **Relevant Offers**: 0
- **Strong Matches**: 0

#### Offers:

1. Frontend Developer (React) — Not relevant
2. Full Stack Engineer (Node.js, React) — Not relevant

#### Skill Frequency:

- JavaScript: 2x
- React: 2x
- (No Data/BI/AI skills)

#### Recruitment Intensity:

- **Intensity: LOW** (< 3 offers, < 1 relevant)

#### Priority Score:

```
- Fit base: 0.0 × 40 = 0 points
- Offer volume: 0 points (no relevant)
- Best fit bonus: 0 points
- Intensity bonus (LOW): 0 points

Total: 0
```

#### Priority Reasons:

1. "No relevant Data/BI/AI offers"

---

## Phase 4 Final Ranking Output

```
======================================================================
COMPANY OUTREACH PRIORITY RANKING
======================================================================

1. Sidel — 80
   Fit profil: 81%
   Recrutement: HIGH
   Offres pertinentes: 5
   Compétences: Python 5x · SQL 4x · Power BI 2x · Excel 1x
   5 offre(s) très compatible(s)

2. TechCorp — 67
   Fit profil: 58%
   Recrutement: HIGH
   Offres pertinentes: 6
   Compétences: Python 6x · SQL 5x · Machine Learning 4x · Spark 3x
   2 offre(s) très compatible(s)

3. Enterprise A — 45
   Fit profil: 62%
   Recrutement: MEDIUM
   Offres pertinentes: 3
   Compétences: SQL 3x · Power BI 2x · Python 1x

4. DataCorp — 42
   Fit profil: 70%
   Recrutement: LOW
   Offres pertinentes: 1
   Compétences: Python 1x · SQL 1x

5. StartupXYZ — 0
   Fit profil: 0%
   Recrutement: LOW
   Offres pertinentes: 0

======================================================================
```

## Key Insights from Output

1. **Sidel is the top priority**: High fit (81%), high hiring volume (5 relevant offers), 3 strong matches with verified evidence

2. **TechCorp is secondary**: Similar high hiring intensity, but moderate fit (58%) — good volume but fewer perfect matches

3. **Enterprise A is tertiary**: Better fit than TechCorp (62%) but lower volume — selective opportunity

4. **DataCorp is niche**: Highest fit (70%) but LOW intensity — single offer, not actively recruiting

5. **StartupXYZ is irrelevant**: No Data/BI/AI focus — skip for now

## What This Answers

> "Which companies should I prioritize based on their current hiring activity and fit with my real profile?"

**Answer from Phase 4:**
- **Maximum opportunity**: Sidel (highest fit + highest volume)
- **Volume play**: TechCorp (more offers, some fit)
- **Selective outreach**: Enterprise A, DataCorp (better fit, lower volume)
- **Skip**: StartupXYZ (no relevant openings)

## What Phase 5 Will Do (Next)

Once Sidel/TechCorp are identified as top priorities, Phase 5 will:
- Extract hiring contacts for top-3 companies ONLY
- Verify contact details via LinkedIn
- Generate personalized outreach emails
- Track outreach attempts

**Phase 4 does NOT do any of this.** It only answers: "Who should I focus on?"
