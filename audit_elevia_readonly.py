"""
READ-ONLY audit of Elevia API configuration and catalogue.

Does NOT modify data. Does NOT expose secrets.
Returns ONLY factual findings about authentication, endpoints, and data characteristics.
"""

import sys
import asyncio
import os
from pathlib import Path
from typing import Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from app.config import config
from app.services.elevia_client import EleviaClient


async def audit_elevia_readonly():
    """Perform read-only audit of Elevia API."""

    report = {}

    # ============================================================================
    # 1. AUTHENTICATION CONFIGURATION
    # ============================================================================

    print("\n" + "=" * 100)
    print("1. ELEVIA AUTHENTICATION & CONFIGURATION")
    print("=" * 100)

    report["ELEVIA_AUTH"] = {
        "ENABLED": "YES" if config.ELEVIA_ENABLED else "NO",
        "API_KEY_PRESENT": "YES" if config.ELEVIA_API_KEY else "NO",
        "API_KEY_LENGTH": len(config.ELEVIA_API_KEY) if config.ELEVIA_API_KEY else 0,
        "BASE_URL": config.ELEVIA_BASE_URL,
        "AUTH_METHOD": "Bearer Token" if config.ELEVIA_API_KEY else "None",
    }

    for key, value in report["ELEVIA_AUTH"].items():
        if key != "API_KEY_LENGTH":
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {value} chars")

    if not config.ELEVIA_ENABLED:
        print("\n⚠️  ELEVIA is DISABLED. Cannot perform audit.")
        report["AUDIT_STATUS"] = "BLOCKED_DISABLED"
        return report

    if not config.ELEVIA_API_KEY:
        print("\n❌ ELEVIA_API_KEY is NOT SET. Cannot authenticate.")
        report["AUDIT_STATUS"] = "BLOCKED_NO_CREDENTIALS"
        return report

    # ============================================================================
    # 2. ELEVIA API ENDPOINTS (from code inspection)
    # ============================================================================

    print("\n" + "=" * 100)
    print("2. ELEVIA API ENDPOINTS (from code)")
    print("=" * 100)

    report["ELEVIA_ENDPOINTS"] = {
        "HEALTH": f"{config.ELEVIA_BASE_URL}/api/health",
        "INGESTION_STATUS": f"{config.ELEVIA_BASE_URL}/ingestion/latest",
        "OFFERS_CATALOG": f"{config.ELEVIA_BASE_URL}/offers/recent",
        "OFFER_DETAIL": f"{config.ELEVIA_BASE_URL}/offers/{{offer_id}}",
        "SEARCH_OFFERS": "NOT_IMPLEMENTED_IN_CLIENT",
        "PROFILE_UPLOAD": f"{config.ELEVIA_BASE_URL}/api/profile/parse-file",
        "GET_PROFILE": f"{config.ELEVIA_BASE_URL}/api/profiles/{{profile_id}}",
        "MATCH_PROFILE": f"{config.ELEVIA_BASE_URL}/api/v1/match",
    }

    for endpoint, url in report["ELEVIA_ENDPOINTS"].items():
        print(f"  {endpoint}: {url}")

    # ============================================================================
    # 3. HEALTH CHECK
    # ============================================================================

    print("\n" + "=" * 100)
    print("3. API HEALTH CHECK")
    print("=" * 100)

    client = EleviaClient(
        base_url=config.ELEVIA_BASE_URL,
        api_key=config.ELEVIA_API_KEY,
    )

    try:
        is_healthy = await client.health_check()
        report["API_HEALTHY"] = "YES" if is_healthy else "NO"
        print(f"  API Status: {'✅ HEALTHY' if is_healthy else '❌ UNHEALTHY'}")
    except Exception as e:
        report["API_HEALTHY"] = "UNKNOWN"
        print(f"  API Status: ⚠️  CANNOT_VERIFY ({str(e)[:50]}...)")

    # ============================================================================
    # 4. INGESTION STATUS
    # ============================================================================

    print("\n" + "=" * 100)
    print("4. INGESTION METADATA")
    print("=" * 100)

    try:
        ingestion = await client.get_ingestion_status()
        report["INGESTION_STATUS"] = ingestion
        print(f"  Latest ingestion:")
        for key, value in ingestion.items():
            print(f"    {key}: {value}")
    except Exception as e:
        print(f"  ⚠️  Ingestion status unavailable: {str(e)[:80]}")
        report["INGESTION_STATUS"] = None

    # ============================================================================
    # 5. CATALOGUE STRUCTURE & SAMPLE
    # ============================================================================

    print("\n" + "=" * 100)
    print("5. CATALOGUE STRUCTURE (READ-ONLY SAMPLE)")
    print("=" * 100)

    try:
        response = await client.get_offers_catalog(limit=1)
        offers = response.get("offers", [])

        if not offers:
            print("  ❌ No offers returned in sample")
            report["CATALOGUE_SIZE"] = 0
            report["SAMPLE_OFFER"] = None
        else:
            first_offer = offers[0]
            print(f"\n  Sample offer (first in /offers/recent):")
            print(f"    Fields present: {list(first_offer.keys())}")
            print(f"    Sample data:")
            for key in ["id", "title", "company", "location", "contract_type"]:
                if key in first_offer:
                    value = first_offer[key]
                    if isinstance(value, str):
                        preview = (value[:50] + "...") if len(value) > 50 else value
                    else:
                        preview = str(value)[:50]
                    print(f"      {key}: {preview}")

            report["SAMPLE_OFFER_FIELDS"] = list(first_offer.keys())
            report["SAMPLE_OFFER"] = {k: str(v)[:100] for k, v in first_offer.items()}

    except Exception as e:
        print(f"  ❌ Catalogue fetch failed: {str(e)[:80]}")
        report["SAMPLE_OFFER"] = None

    # ============================================================================
    # 6. PAGINATION & LIMITS
    # ============================================================================

    print("\n" + "=" * 100)
    print("6. PAGINATION PARAMETERS")
    print("=" * 100)

    report["PAGINATION"] = {
        "DEFAULT_LIMIT": 50,
        "TEST_LIMITS": [10, 50, 100, 500],
        "SUPPORTS_SKIP": "UNKNOWN (not in client code)",
    }

    print(f"  Default limit: {report['PAGINATION']['DEFAULT_LIMIT']}")
    print(f"  Supports pagination: UNKNOWN (need to test)")

    # ============================================================================
    # 7. SCHEMA ANALYSIS (from normalized schema)
    # ============================================================================

    print("\n" + "=" * 100)
    print("7. NORMALIZED SCHEMA (what we preserve)")
    print("=" * 100)

    report["NORMALIZED_SCHEMA"] = {
        "CATALOG_ENTRY": {
            "offer_id": "str",
            "title": "str",
            "company": "str",
            "location": "str",
            "description": "str (optional)",
            "contract_type": "str (optional)",
            "mission_duration": "str (optional)",
            "source_type": "str (fixed='elevia')",
        },
        "OFFER_DETAIL": {
            "offer_id": "str",
            "title": "str",
            "company": "str",
            "location": "str",
            "description": "str",
            "full_text": "str",
            "contract_type": "str (optional)",
            "mission_duration": "str (optional)",
            "required_skills": "list[str]",
            "soft_skills": "list[str]",
            "salary_range": "dict (optional)",
            "ats_keywords": "list[str]",
            "raw_data": "dict (PRESERVES ALL ORIGINAL FIELDS)",
        },
    }

    print("\n  Catalog Entry fields:")
    for field, ftype in report["NORMALIZED_SCHEMA"]["CATALOG_ENTRY"].items():
        print(f"    {field}: {ftype}")

    print("\n  Offer Detail fields:")
    for field, ftype in report["NORMALIZED_SCHEMA"]["OFFER_DETAIL"].items():
        print(f"    {field}: {ftype}")

    # ============================================================================
    # 8. MISSING IMPLEMENTATION
    # ============================================================================

    print("\n" + "=" * 100)
    print("8. IMPLEMENTATION GAPS")
    print("=" * 100)

    report["IMPLEMENTATION_GAPS"] = [
        "search_offers() is called in gateway but NOT implemented in EleviaClient",
        "Pagination parameters (skip/offset) not exposed in client methods",
        "No timestamp fields for offer publication or ingestion date",
        "No offer status field (active/expired/withdrawn)",
        "No first_seen_at or last_seen_at tracking",
    ]

    for gap in report["IMPLEMENTATION_GAPS"]:
        print(f"  ⚠️  {gap}")

    # ============================================================================
    # SUMMARY
    # ============================================================================

    print("\n" + "=" * 100)
    print("AUDIT SUMMARY")
    print("=" * 100)

    print(f"\nELEVIA_ENABLED: {report['ELEVIA_AUTH']['ENABLED']}")
    print(f"ELEVIA_API_KEY_PRESENT: {report['ELEVIA_AUTH']['API_KEY_PRESENT']}")
    print(f"API_HEALTHY: {report.get('API_HEALTHY', 'UNKNOWN')}")
    print(f"AUDIT_STATUS: {report.get('AUDIT_STATUS', 'READY_FOR_DATA_AUDIT')}")

    return report


if __name__ == "__main__":
    report = asyncio.run(audit_elevia_readonly())
    print("\n[END OF AUDIT]\n")
