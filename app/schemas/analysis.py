from pydantic import BaseModel
from typing import List, Optional

class JobAnalysisResult(BaseModel):
    company: str
    job_title: str
    sector: str
    seniority: str
    missions: List[str]
    required_skills: List[str]
    soft_skills: List[str]
    ats_keywords: List[str]
    candidate_profile_needed: str
    recommended_angle: str
    match_score: int
    strengths: List[str]
    missing_points: List[str]
    cv_strategy: str
    profile_blocks_to_use: List[int]
    profile_blocks_to_avoid: List[int]
    risk_of_overclaiming: List[str]

class MatchingResult(BaseModel):
    match_score: int
    strengths: List[str]
    missing_points: List[str]
    cv_strategy: str
    recommended_angle: str
