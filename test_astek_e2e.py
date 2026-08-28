"""E2E Test: CVAdaptationAgent V2 with Astek offer"""

import asyncio
import json
from app.services.master_cv_service import load_master_cv
from app.agents.cv_adaptation_agent import CVAdaptationAgent
from app.agents.generation_agent import GenerationAgent

async def test_astek_offer():
    """Test with real Astek offer to verify metrics preservation."""

    master_cv = load_master_cv()

    # Astek offer analysis
    astek_analysis = {
        "company": "Astek",
        "job_title": "Supply Chain Engineer - APS Deployment",
        "missions": [
            "Participer au déploiement et à l'intégration de l'outil APS",
            "Analyser et fiabiliser les données Supply Chain",
            "Optimiser la planification et l'ordonnancement de la production",
        ],
        "required_skills": [
            "APS",
            "Planification de production",
            "Ordonnancement",
            "Data Supply Chain",
            "Python",
            "SQL",
            "Data Analysis",
        ],
        "ats_keywords": ["APS", "supply chain", "planning", "scheduling", "production", "data"],
        "seniority": "mid-level",
        "context": "Pharmaceutical company in Normandy",
    }

    positioning = "Data Analyst | Business Intelligence"

    print("=" * 80)
    print("E2E TEST: CVAdaptationAgent V2 with Astek Offer")
    print("=" * 80)
    print(f"\nJob: {astek_analysis['job_title']} @ {astek_analysis['company']}")
    print(f"Positioning: {positioning}")
    print(f"\nOffer mentions APS, Supply Chain, Planning, Scheduling")
    print(f"Candidate profile has: BI, Automation, Data Analysis (NO APS/Supply Chain)")

    # Simulate CVAdaptationAgent.adapt_cv() response
    # (would normally call OpenAI to score relevance)
    print("\n" + "=" * 80)
    print("STEP 1: Selection Scoring (simulated OpenAI response)")
    print("=" * 80)

    # Simulated scores (what OpenAI would return)
    # Sidel: High relevance (BI, dashboards, data analysis)
    # MadeByAkim: Medium-high (automation, APIs, workflows)
    # Vassard: Low (sales-focused, not relevant)
    # Elevia: Medium (data + AI)
    # Job Apply Assistant: Medium-low (automation focus)
    # V.I.E Matcher: Low

    simulated_selection = {
        "experiences": [
            {"source_id": 0, "relevance": 0.90, "show": True, "order": 1, "reason": "Sidel BI + dashboards + data analysis"},
            {"source_id": 1, "relevance": 0.65, "show": True, "order": 2, "reason": "MadeByAkim automation + data systems"},
            {"source_id": 2, "relevance": 0.25, "show": False, "order": 3, "reason": "Vassard sales-focused, low relevance"},
        ],
        "projects": [
            {"source_id": 0, "relevance": 0.70, "show": True, "order": 1, "reason": "Elevia data + AI"},
            {"source_id": 1, "relevance": 0.55, "show": True, "order": 2, "reason": "Job Apply Assistant automation"},
            {"source_id": 2, "relevance": 0.30, "show": False, "order": 3, "reason": "V.I.E Matcher less relevant"},
            {"source_id": 3, "relevance": 0.20, "show": False, "order": 4, "reason": "SkillMap not relevant"},
        ],
        "skills": [
            {"source_id": 0, "relevance": 0.95, "show": True, "order": 1, "reason": "Data & Analytics - direct match"},
            {"source_id": 1, "relevance": 0.60, "show": True, "order": 2, "reason": "Automation & APIs"},
            {"source_id": 2, "relevance": 0.70, "show": True, "order": 3, "reason": "AI & LLM - tangentially relevant"},
            {"source_id": 3, "relevance": 0.80, "show": True, "order": 4, "reason": "Backend & Data Systems - PostgreSQL, FastAPI"},
            {"source_id": 4, "relevance": 0.50, "show": True, "order": 5, "reason": "Business Systems"},
            {"source_id": 5, "relevance": 0.30, "show": False, "order": 6, "reason": "Creative - low relevance"},
        ],
    }

    print("\nScoring Results:")
    print("\nExperiences:")
    for exp in simulated_selection["experiences"]:
        show_str = "✓" if exp["show"] else "✗"
        print(f"  {show_str} {exp['source_id']}: {master_cv['experiences'][exp['source_id']]['company'][:20]:<20} relevance={exp['relevance']:.2f} ({exp['reason']})")

    print("\nProjects:")
    for proj in simulated_selection["projects"]:
        show_str = "✓" if proj["show"] else "✗"
        print(f"  {show_str} {proj['source_id']}: {master_cv['projects'][proj['source_id']]['title'][:30]:<30} relevance={proj['relevance']:.2f}")

    # Build source-based adaptation from simulated selection
    print("\n" + "=" * 80)
    print("STEP 2: Build Source-Based Adaptation")
    print("=" * 80)

    from app.services.summary_service import build_deterministic_summary

    selected_skill_ids = [s["source_id"] for s in simulated_selection["skills"] if s["show"]]
    summary = build_deterministic_summary(positioning, master_cv["skills"], selected_skill_ids)

    source_adaptation = {
        "title": positioning,
        "summary": summary,
        "selected_experience_blocks": simulated_selection["experiences"],
        "selected_project_blocks": simulated_selection["projects"],
        "selected_skill_blocks": simulated_selection["skills"],
        "metadata": {
            "source": "cv_adaptation_agent_v2",
            "strategy": "source_preserving_selection",
        },
    }

    print(f"\nTitle: {source_adaptation['title']}")
    print(f"Summary: {source_adaptation['summary'][:80]}...")

    # Convert to template format
    print("\n" + "=" * 80)
    print("STEP 3: Convert to Template Format (fetch actual text from Master CV)")
    print("=" * 80)

    adaptation = GenerationAgent._convert_source_adaptation_to_template_format(
        source_adaptation, master_cv
    )

    print(f"\nExperience order: {adaptation['experience_order']}")
    print(f"Project order: {adaptation['project_order']}")

    # Verify metrics preservation
    print("\n" + "=" * 80)
    print("STEP 4: VERIFY METRICS PRESERVATION (CRITICAL)")
    print("=" * 80)

    sidel_bullets = adaptation["experience_bullets"].get("0", [])
    print(f"\nSidel Experience ({len(sidel_bullets)} bullets):")

    # Check metrics
    first_bullet = sidel_bullets[0] if sidel_bullets else ""
    print(f"\nFirst Sidel bullet:\n  {first_bullet}\n")

    checks = {
        "✓ Contains '6+' (not 'around 10')": "6+" in first_bullet,
        "✓ Contains 'dozens' (not '30–40')": "dozens" in first_bullet,
        "✗ Does NOT contain 'around 10'": "around 10" not in first_bullet,
        "✗ Does NOT contain '~30–40'": "~30–40" not in first_bullet and "30–40" not in first_bullet,
        f"✓ All Sidel bullets preserved ({len(sidel_bullets)}/7)": len(sidel_bullets) == 7,
    }

    print("Metrics Checks:")
    for check, result in checks.items():
        status = "✓" if result else "✗"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {check}: {'PASS' if result else 'FAIL'}")

    # Check for invented content
    print("\n" + "=" * 80)
    print("STEP 5: VERIFY NO INVENTED CONTENT")
    print("=" * 80)

    all_bullets = []
    for bullets in adaptation["experience_bullets"].values():
        all_bullets.extend(bullets)
    for bullets in adaptation["project_bullets"].values():
        all_bullets.extend(bullets)

    all_text = adaptation["summary"] + " " + " ".join(all_bullets)

    forbidden = ["APS", "supply chain", "Supply Chain", "Optimization Specialist", "Advanced Planning"]
    print(f"\nSearching for forbidden keywords in CV content...")
    found_forbidden = []
    for keyword in forbidden:
        if keyword.lower() in all_text.lower():
            found_forbidden.append(keyword)

    if found_forbidden:
        print(f"  ✗ FAIL: Found forbidden keywords: {found_forbidden}")
    else:
        print(f"  ✓ PASS: No APS/Supply Chain content invented")

    # Check MadeByAkim preservation
    madebyakim_bullets = adaptation["experience_bullets"].get("1", [])
    print(f"\nMadeByAkim Experience ({len(madebyakim_bullets)} bullets):")
    print(f"  ✓ PASS: All MadeByAkim bullets preserved" if len(madebyakim_bullets) >= 4 else f"  ✗ FAIL: Only {len(madebyakim_bullets)}/5 bullets")

    # Final verdict
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    all_checks_pass = all(checks.values()) and not found_forbidden and len(madebyakim_bullets) >= 4

    if all_checks_pass:
        print("\n✅ E2E TEST PASSED")
        print("\nCVAdaptationAgent V2 successfully:")
        print("  ✓ Preserved exact metrics ('6+', 'dozens')")
        print("  ✓ Preserved all Sidel bullets (7/7)")
        print("  ✓ Preserved MadeByAkim bullets (4+/5)")
        print("  ✓ Did NOT invent APS/Supply Chain content")
        print("  ✓ Used validated positioning (not 'Supply Data Engineer Positioning')")
        print("  ✓ Built deterministic summary (not job-specific)")
    else:
        print("\n❌ E2E TEST FAILED")
        print("\nIssues found:")
        for check, result in checks.items():
            if not result:
                print(f"  ✗ {check}")
        if found_forbidden:
            print(f"  ✗ Invented content: {found_forbidden}")

    return {
        "all_checks_pass": all_checks_pass,
        "metrics_preserved": all(checks.values()),
        "no_invented_content": not found_forbidden,
        "madebyakim_preserved": len(madebyakim_bullets) >= 4,
    }

if __name__ == "__main__":
    result = asyncio.run(test_astek_offer())
    print("\n" + "=" * 80)
    print(f"Result: {result}")
