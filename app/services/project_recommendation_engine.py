import logging
from typing import List, Dict, Any
from app.services.skill_gap_aggregation_service import SkillGapAggregationService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ProjectRecommendation:
    """A recommended project idea."""

    def __init__(
        self,
        title: str,
        description: str,
        solves_gaps: List[str],
        key_skills: List[str],
        impact: str,  # "high", "medium", "low"
        difficulty: str,  # "beginner", "intermediate", "advanced"
        estimated_hours: int,
        portfolio_value: str,  # "high", "medium", "low"
    ):
        self.title = title
        self.description = description
        self.solves_gaps = solves_gaps
        self.key_skills = key_skills
        self.impact = impact
        self.difficulty = difficulty
        self.estimated_hours = estimated_hours
        self.portfolio_value = portfolio_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "solves_gaps": self.solves_gaps,
            "key_skills": self.key_skills,
            "impact": self.impact,
            "difficulty": self.difficulty,
            "estimated_hours": self.estimated_hours,
            "portfolio_value": self.portfolio_value,
        }

    def calculate_roi_score(self) -> float:
        """
        Calculate ROI score based on:
        - number of gaps solved
        - impact level
        - portfolio value
        - difficulty (inverse)
        """
        impact_multiplier = {"high": 3, "medium": 2, "low": 1}[self.impact]
        portfolio_multiplier = {"high": 3, "medium": 2, "low": 1}[self.portfolio_value]
        difficulty_multiplier = {"beginner": 3, "intermediate": 2, "advanced": 1}[self.difficulty]

        roi = (
            len(self.solves_gaps)
            * impact_multiplier
            * portfolio_multiplier
            * difficulty_multiplier
        )
        return roi


class ProjectRecommendationEngine:
    """Generate portfolio project recommendations based on skill gaps."""

    # Project templates indexed by gap skills
    PROJECTS = [
        ProjectRecommendation(
            title="Modern Data Stack Portfolio Project",
            description="Build a complete data pipeline with dbt, Airflow, and BI tools",
            solves_gaps=["dbt", "data modeling", "sql"],
            key_skills=["Python", "PostgreSQL", "dbt", "Airflow", "Data Visualization"],
            impact="high",
            difficulty="intermediate",
            estimated_hours=40,
            portfolio_value="high",
        ),
        ProjectRecommendation(
            title="Job Market Observatory - Airflow Pipeline",
            description="Build an Airflow DAG that scrapes job listings, processes them, and generates reports",
            solves_gaps=["airflow", "orchestration", "automation"],
            key_skills=["Python", "Airflow", "Scraping", "Data Processing", "Scheduling"],
            impact="high",
            difficulty="intermediate",
            estimated_hours=50,
            portfolio_value="high",
        ),
        ProjectRecommendation(
            title="Cloud Deployment of Microservice",
            description="Deploy a containerized application to AWS/GCP with CI/CD pipeline",
            solves_gaps=["aws", "gcp", "docker", "kubernetes", "devops"],
            key_skills=["Docker", "Kubernetes", "Cloud Platform", "CI/CD", "DevOps"],
            impact="high",
            difficulty="advanced",
            estimated_hours=60,
            portfolio_value="high",
        ),
        ProjectRecommendation(
            title="Real-time Analytics Dashboard",
            description="Build a real-time dashboard using Tableau, Power BI, or similar",
            solves_gaps=["power bi", "tableau", "visualization", "analytics"],
            key_skills=["BI Tool", "SQL", "Data Analysis", "Visualization", "Dashboard Design"],
            impact="high",
            difficulty="intermediate",
            estimated_hours=35,
            portfolio_value="high",
        ),
        ProjectRecommendation(
            title="Spark Data Processing Pipeline",
            description="Build a distributed data processing pipeline with Apache Spark",
            solves_gaps=["spark", "distributed computing", "big data"],
            key_skills=["Python", "Spark", "Big Data", "Distributed Computing"],
            impact="high",
            difficulty="advanced",
            estimated_hours=55,
            portfolio_value="high",
        ),
        ProjectRecommendation(
            title="Machine Learning Model in Production",
            description="Build and deploy an ML model with model versioning and monitoring",
            solves_gaps=["mlops", "machine learning", "model deployment"],
            key_skills=["Python", "ML Frameworks", "MLOps", "Model Serving"],
            impact="high",
            difficulty="advanced",
            estimated_hours=70,
            portfolio_value="high",
        ),
        ProjectRecommendation(
            title="REST API Design & Documentation",
            description="Build a well-documented REST API with authentication and testing",
            solves_gaps=["api design", "rest", "backend"],
            key_skills=["Python/Node/Go", "REST API", "Authentication", "Testing", "Documentation"],
            impact="medium",
            difficulty="intermediate",
            estimated_hours=30,
            portfolio_value="medium",
        ),
        ProjectRecommendation(
            title="Git Workflow & CI/CD Automation",
            description="Set up Git workflows, automated testing, and CI/CD pipelines",
            solves_gaps=["git", "ci/cd", "automation", "testing"],
            key_skills=["Git", "CI/CD Tools", "Testing", "Automation"],
            impact="medium",
            difficulty="beginner",
            estimated_hours=20,
            portfolio_value="medium",
        ),
        ProjectRecommendation(
            title="Data Quality & Testing Framework",
            description="Build automated tests for data pipelines and data quality checks",
            solves_gaps=["data quality", "testing", "validation"],
            key_skills=["Python", "Testing", "Data Validation", "SQL"],
            impact="medium",
            difficulty="intermediate",
            estimated_hours=25,
            portfolio_value="medium",
        ),
        ProjectRecommendation(
            title="Documentation & Knowledge Base",
            description="Create comprehensive project documentation with diagrams and examples",
            solves_gaps=["documentation", "communication", "technical writing"],
            key_skills=["Technical Writing", "Diagramming", "Documentation Tools"],
            impact="medium",
            difficulty="beginner",
            estimated_hours=15,
            portfolio_value="medium",
        ),
    ]

    @staticmethod
    def get_recommendations(
        db: Session,
        telegram_user_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate project recommendations based on critical gaps.
        """
        # Get critical gaps
        critical_gaps = SkillGapAggregationService.calculate_critical_gaps(
            db, telegram_user_id, limit=15
        )

        if not critical_gaps:
            return []

        # Extract gap skills
        gap_skills = [gap["skill"].lower() for gap in critical_gaps]

        # Find matching projects
        matched_projects = []
        for project in ProjectRecommendationEngine.PROJECTS:
            solves = [
                gap for gap in gap_skills
                if any(gap in skill.lower() for skill in project.solves_gaps)
            ]

            if solves:
                matched_projects.append({
                    "project": project.to_dict(),
                    "solves_count": len(solves),
                    "solved_gaps": solves,
                    "roi_score": project.calculate_roi_score(),
                })

        # Sort by ROI and number of gaps solved
        matched_projects.sort(
            key=lambda x: (x["roi_score"], x["solves_count"]),
            reverse=True,
        )

        # Return top projects with metadata
        return [
            {
                "rank": i + 1,
                "title": p["project"]["title"],
                "description": p["project"]["description"],
                "solved_gaps": p["solved_gaps"],
                "key_skills": p["project"]["key_skills"],
                "impact": p["project"]["impact"],
                "difficulty": p["project"]["difficulty"],
                "estimated_hours": p["project"]["estimated_hours"],
                "portfolio_value": p["project"]["portfolio_value"],
                "roi_score": p["roi_score"],
            }
            for i, p in enumerate(matched_projects[:limit])
        ]

    @staticmethod
    def get_project_by_title(title: str) -> Dict[str, Any]:
        """Get full project details by title."""
        for project in ProjectRecommendationEngine.PROJECTS:
            if project.title.lower() == title.lower():
                return project.to_dict()
        return {}
