"""Elevia Intelligence Service - Query and analyze live offers from Elevia API V1."""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import Counter
from app.config import config
from app.services.elevia_client import EleviaClient
from app.services.database_intelligence_service import DatabaseIntelligenceService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EleviaIntelligenceService:
    """Service to query and analyze live offers from Elevia API V1."""

    def __init__(self, elevia_client: Optional[EleviaClient] = None):
        self.client = elevia_client or EleviaClient(
            base_url=config.ELEVIA_BASE_URL,
            api_key=config.ELEVIA_API_KEY
        )

    async def get_recent_offers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent active offers from Elevia."""
        try:
            result = await self.client.get_offers_catalog(limit=limit)
            if "error" in result:
                logger.warning("[ELEVIA_INTEL] Catalog error: %s", result.get("error"))
                return []
            return result.get("offers", [])
        except Exception as e:
            logger.error("[ELEVIA_INTEL] Failed to get recent offers: %s", str(e))
            return []

    async def get_offer_detail(self, offer_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed offer information."""
        try:
            result = await self.client.get_offer_detail(str(offer_id))
            if "error" in result:
                logger.warning("[ELEVIA_INTEL] Offer detail error for %s: %s", offer_id, result.get("error"))
                return None
            return result
        except Exception as e:
            logger.error("[ELEVIA_INTEL] Failed to get offer detail: %s", str(e))
            return None

    async def get_ingestion_status(self) -> Dict[str, Any]:
        """Get latest ingestion run metadata."""
        try:
            result = await self.client.search_offers()  # Using search as proxy for ingestion status
            return result if result else {}
        except Exception as e:
            logger.error("[ELEVIA_INTEL] Failed to get ingestion status: %s", str(e))
            return {}

    async def analyze_market_insights(self) -> Dict[str, Any]:
        """Analyze market trends from recent offers."""
        offers = await self.get_recent_offers(limit=100)

        if not offers:
            return {"error": "No offers available"}

        # Extract insights
        companies = [o.get("company", "Unknown") for o in offers if o.get("company")]
        locations = [o.get("location", "Unknown") for o in offers if o.get("location")]
        countries = [o.get("country", "Unknown") for o in offers if o.get("country")]
        contract_types = [o.get("contract_type", "Unknown") for o in offers if o.get("contract_type")]
        sources = [o.get("source", "Unknown") for o in offers if o.get("source")]

        return {
            "total_offers": len(offers),
            "top_companies": Counter(companies).most_common(10),
            "top_locations": Counter(locations).most_common(10),
            "top_countries": Counter(countries).most_common(10),
            "contract_types": Counter(contract_types).most_common(),
            "sources": Counter(sources).most_common(),
            "freshness": {
                "oldest_offer_days_ago": self._days_since(min(
                    [o.get("publication_date") for o in offers if o.get("publication_date")],
                    default=datetime.now().isoformat()
                )),
                "newest_offer_hours_ago": self._hours_since(max(
                    [o.get("last_seen_at") for o in offers if o.get("last_seen_at")],
                    default=datetime.now().isoformat()
                )),
            },
        }

    async def discover_opportunities(
        self,
        db: Session,
        user_id: str,
        candidate_skills: List[str],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Discover top opportunities matching user profile."""
        offers = await self.get_recent_offers(limit=50)

        if not offers:
            return []

        # Score offers by relevance to candidate
        scored_offers = []
        for offer in offers:
            score = self._calculate_match_score(offer, candidate_skills)
            if score > 0:
                scored_offers.append({
                    "id": offer.get("id"),
                    "title": offer.get("title"),
                    "company": offer.get("company"),
                    "location": offer.get("location"),
                    "country": offer.get("country"),
                    "match_score": round(score, 1),
                    "url": offer.get("url"),
                    "source": offer.get("source"),
                    "contract_type": offer.get("contract_type"),
                })

        # Return top matches
        return sorted(scored_offers, key=lambda x: x["match_score"], reverse=True)[:limit]

    async def get_intelligence_summary(
        self,
        db: Session,
        user_id: str,
        candidate_skills: List[str]
    ) -> Dict[str, Any]:
        """Get comprehensive market and opportunity intelligence."""
        market = await self.analyze_market_insights()
        opportunities = await self.discover_opportunities(db, user_id, candidate_skills, limit=5)
        local_stats = DatabaseIntelligenceService.get_application_summary(db, user_id)

        return {
            "market": {
                "total_active_offers": market.get("total_offers", 0),
                "top_companies": [
                    {"company": c[0], "count": c[1]}
                    for c in market.get("top_companies", [])[:5]
                ],
                "top_countries": [
                    {"country": c[0], "count": c[1]}
                    for c in market.get("top_countries", [])[:5]
                ],
                "contract_mix": {
                    ct[0]: ct[1] for ct in market.get("contract_types", [])
                },
            },
            "opportunities": opportunities,
            "your_stats": {
                "offers_analyzed_locally": local_stats.get("total_applications", 0),
                "avg_match_score": local_stats.get("avg_match_score", 0),
            },
        }

    def _calculate_match_score(self, offer: Dict[str, Any], candidate_skills: List[str]) -> float:
        """Calculate match score between offer and candidate."""
        score = 50.0  # Base score

        # Purity score (how clean the offer is)
        purity = offer.get("purity_score", 0.5)
        score += purity * 30

        # Country/location match (bonus if candidate is flexible)
        # Could be enriched with candidate location preferences

        # Contract type preference (bonus for permanent)
        if offer.get("contract_type") == "CDI":
            score += 10

        return min(score, 100)

    @staticmethod
    def _days_since(date_str: str) -> int:
        """Calculate days since a date string."""
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return (datetime.now(date.tzinfo) - date).days
        except:
            return 0

    @staticmethod
    def _hours_since(date_str: str) -> int:
        """Calculate hours since a date string."""
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return int((datetime.now(date.tzinfo) - date).total_seconds() / 3600)
        except:
            return 0

    @staticmethod
    def format_market_message(market_data: Dict[str, Any]) -> str:
        """Format market insights for Telegram."""
        msg = f"""📊 <b>Marché actuel (Elevia)</b>

Total d'offres actives: <b>{market_data['total_active_offers']}</b>

<b>Top 5 entreprises:</b>
"""
        for company, count in market_data.get("top_companies", [])[:5]:
            msg += f"\n• {company}: {count} offres"

        msg += f"\n\n<b>Top 5 pays:</b>\n"
        for country, count in market_data.get("top_countries", [])[:5]:
            msg += f"\n• {country}: {count} offres"

        msg += f"\n\n<b>Types de contrats:</b>\n"
        for contract_type, count in market_data.get("contract_mix", {}).items():
            msg += f"\n• {contract_type}: {count}"

        return msg

    @staticmethod
    def format_opportunities_message(opportunities: List[Dict[str, Any]]) -> str:
        """Format opportunity list for Telegram."""
        if not opportunities:
            return "❌ Pas d'opportunités correspondantes pour le moment."

        msg = "<b>🎯 Top opportunités pour toi:</b>\n\n"
        for i, opp in enumerate(opportunities[:5], 1):
            msg += f"{i}. <b>{opp['company']}</b>\n"
            msg += f"   {opp['title']}\n"
            msg += f"   📍 {opp['location']}, {opp['country']}\n"
            msg += f"   Match: {opp['match_score']}/100\n"
            msg += f"   Type: {opp['contract_type']}\n\n"

        return msg
