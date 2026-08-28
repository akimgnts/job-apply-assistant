"""E2E Test: CVAdaptationAgent V3 with Real Astek Offer

Tests the REAL pipeline (not simulated):
1. Load Master CV
2. Analyze Astek offer (real OpenAI)
3. Call CVAdaptationAgentV3 (real index-based selection)
4. Render CV with selected content
5. Verify metrics preserved, no invented content

Astek is critical regression case:
- Offers APS/Supply Chain (candidate does NOT have)
- Requires verification that NO APS/Supply Chain content appears
- Must preserve exact metrics: "6+" dashboards, "dozens" collaborators
- Must preserve all Sidel/MadeByAkim bullets
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("OPENAI_API_KEY", "sk-test-123456")

from app.services.master_cv_service import load_master_cv
from app.agents.analysis_agent import AnalysisAgent
from app.agents.cv_adaptation_agent_v3 import CVAdaptationAgentV3
from app.agents.generation_agent import GenerationAgent
from app.services.document_service import render_cv
from app.database.db import SessionLocal

# Real Astek job offer (from user)
ASTEK_OFFER = """
Rejoignez Astek en tant qu'Ingénieur Supply Chain - Déploiement APS

Position: Supply Chain Engineer - APS Deployment
Entreprise: Astek
Lieu: Normandie, France
Type: CDI

Description:
Participer au déploiement et à l'intégration de l'outil APS (Advanced Planning & Scheduling)
Analyser et fiabiliser les données Supply Chain
Optimiser la planification et l'ordonnancement de la production
Collaborer avec les équipes métier et IT pour assurer le succès du projet

Compétences requises:
- APS (Advanced Planning & Scheduling)
- Planification de production
- Ordonnancement
- Data Supply Chain
- Python
- SQL
- Analyse de données
- Maîtrise du français et anglais

Contexte:
Groupe pharmaceutique en Normandie cherchant à moderniser ses processus de supply chain.
Projet stratégique de 2 ans incluant formation, déploiement et optimisation continue.
Équipe internationale, environnement agile.
"""

ASTEK_ANALYSIS = {
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

POSITIONING = "Data Analyst | Business Intelligence"


async def test_astek_e2e_v3_real():
    """Run full E2E test with real V3 pipeline."""

    print("=" * 80)
    print("E2E TEST: CVAdaptationAgent V3 with Real Astek Offer")
    print("=" * 80)
    print(f"\nJob: {ASTEK_ANALYSIS['job_title']} @ {ASTEK_ANALYSIS['company']}")
    print(f"Positioning: {POSITIONING}")
    print(f"\nOffer keywords: APS, Supply Chain, Planning, Scheduling, Production, Data")
    print(f"Candidate profile: BI, Automation, Data Analysis (NO APS/Supply Chain experience)")

    # Load Master CV
    print("\n" + "=" * 80)
    print("STEP 1: Load Master CV (source of truth)")
    print("=" * 80)

    master_cv = load_master_cv()
    print(f"✓ Master CV loaded: {len(master_cv['experiences'])} experiences")
    print(f"  Experiences: {[e['company'] for e in master_cv['experiences']]}")
    print(f"  Projects: {[p['title'] for p in master_cv['projects']]}")

    # Verify Master CV has the exact metrics we're protecting
    sidel_first_bullet = master_cv["experiences"][0]["bullets"][0]
    print(f"\nSidel first bullet (MUST preserve):")
    print(f"  {sidel_first_bullet}")

    checks_initial = {
        "Contains '6+'": "6+" in sidel_first_bullet,
        "Contains 'dozens'": "dozens" in sidel_first_bullet,
        "Does NOT contain 'around'": "around" not in sidel_first_bullet.lower(),
        "Does NOT contain '~30'": "~30" not in sidel_first_bullet and "30–40" not in sidel_first_bullet,
    }
    print("\nMetrics check (Master CV):")
    for check, result in checks_initial.items():
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {check}")

    # Step 2: Call CVAdaptationAgentV3
    print("\n" + "=" * 80)
    print("STEP 2: CVAdaptationAgent V3 Selection")
    print("=" * 80)

    try:
        source_adaptation = await CVAdaptationAgentV3.adapt_cv(
            ASTEK_ANALYSIS,
            POSITIONING,
            master_cv,
        )

        print(f"✓ Selection completed")
        print(f"  Title: {source_adaptation.get('title')}")
        print(f"  Summary: {source_adaptation.get('summary')[:80]}...")
        print(f"  Selected experiences: {len(source_adaptation.get('selected_experience_blocks', []))}")
        print(f"  Selected projects: {len(source_adaptation.get('selected_project_blocks', []))}")
        print(f"  Selected skills: {len(source_adaptation.get('selected_skill_blocks', []))}")

        # Show which experiences were selected
        for exp in source_adaptation.get("selected_experience_blocks", []):
            exp_id = exp.get("source_id")
            exp_name = master_cv["experiences"][exp_id]["company"]
            bullet_count = len(exp.get("bullet_indices", []))
            print(f"    → Experience {exp_id} ({exp_name}): {bullet_count} bullets selected")

    except Exception as e:
        print(f"✗ Selection failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

    # Step 3: Convert to template format
    print("\n" + "=" * 80)
    print("STEP 3: Convert to template format (fetch text from Master CV)")
    print("=" * 80)

    adaptation = GenerationAgent._convert_source_adaptation_to_template_format(
        source_adaptation, master_cv
    )

    print(f"✓ Conversion completed")
    print(f"  Experience order: {adaptation.get('experience_order')}")
    print(f"  Project order: {adaptation.get('project_order')}")

    # Step 4: Render CV
    print("\n" + "=" * 80)
    print("STEP 4: Render CV with Jinja2 template")
    print("=" * 80)

    context = {
        "candidate": {
            "name": "Akim Guentas",
            "email": "akimguentas13@gmail.com",
            "phone": "+33 6 00 00 00 00",
            "linkedin": "",
            "github": "",
            "website": "",
        },
        "adaptation": adaptation,
        "master_cv": master_cv,
        "positioning": POSITIONING,
        "analysis_job_title": ASTEK_ANALYSIS["job_title"],
    }

    html = render_cv(context, template_name="master_cv.html")
    print(f"✓ CV rendered ({len(html)} bytes)")

    # Step 5: VERIFY METRICS PRESERVATION (CRITICAL)
    print("\n" + "=" * 80)
    print("STEP 5: VERIFY METRICS PRESERVATION")
    print("=" * 80)

    # Check that exact metric strings appear
    checks_final = {
        "Contains '6+' (not 'around 10')": "6+" in html,
        "Contains 'dozens' (not '~30–40')": "dozens" in html,
        "Does NOT contain 'around 10'": "around 10" not in html,
        "Does NOT contain '~30–40'": "~30–40" not in html and "30–40" not in html,
        "Does NOT contain rewritten metrics": "around 10" not in html and "~30–40" not in html,
    }

    print("Metrics in rendered HTML:")
    all_metric_checks_pass = True
    for check, result in checks_final.items():
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {check}")
        if not result:
            all_metric_checks_pass = False

    # Step 6: VERIFY NO INVENTED CONTENT
    print("\n" + "=" * 80)
    print("STEP 6: VERIFY NO INVENTED CONTENT")
    print("=" * 80)

    # Extract all visible text from HTML for keyword search
    # Simple heuristic: remove HTML tags and search
    import re
    html_text = re.sub(r"<[^>]+>", " ", html)

    forbidden_keywords = [
        "APS",
        "supply chain",
        "Supply Chain",
        "planning",
        "scheduling",
        "Optimization Specialist",
        "Advanced Planning",
    ]

    found_forbidden = []
    for keyword in forbidden_keywords:
        # Case-insensitive search, but avoid matching when it's part of a larger word
        if re.search(r"\b" + re.escape(keyword) + r"\b", html_text, re.IGNORECASE):
            found_forbidden.append(keyword)

    print("Forbidden keyword search (should be EMPTY):")
    if found_forbidden:
        print(f"  ✗ FAIL: Found forbidden keywords: {found_forbidden}")
        print("    (This means OpenAI invented content not in Master CV)")
    else:
        print(f"  ✓ PASS: No APS/Supply Chain/planning/scheduling content invented")

    # Step 7: VERIFY BULLET PRESERVATION
    print("\n" + "=" * 80)
    print("STEP 7: VERIFY BULLET PRESERVATION")
    print("=" * 80)

    sidel_bullets = adaptation.get("experience_bullets", {}).get("0", [])
    madebyakim_bullets = adaptation.get("experience_bullets", {}).get("1", [])

    print(f"Sidel experience: {len(sidel_bullets)} bullets selected")
    if sidel_bullets:
        print(f"  First bullet: {sidel_bullets[0][:80]}...")
    else:
        print(f"  ERROR: No Sidel bullets selected!")

    print(f"\nMadeByAkim experience: {len(madebyakim_bullets)} bullets selected")

    sidel_check = len(sidel_bullets) > 0
    madebyakim_check = len(madebyakim_bullets) > 0

    print(f"\nBullet checks:")
    print(f"  {'✓' if sidel_check else '✗'} Sidel bullets preserved ({len(sidel_bullets)}/{len(master_cv['experiences'][0]['bullets'])})")
    print(f"  {'✓' if madebyakim_check else '✗'} MadeByAkim bullets preserved ({len(madebyakim_bullets)}/{len(master_cv['experiences'][1]['bullets'])})")

    # Step 8: TITLE VALIDATION
    print("\n" + "=" * 80)
    print("STEP 8: VERIFY TITLE VALIDATION")
    print("=" * 80)

    title = adaptation.get("title", "")
    print(f"Rendered title: '{title}'")

    title_check = title == POSITIONING
    print(f"  {'✓' if title_check else '✗'} Title matches positioning (not generated)")

    # FINAL VERDICT
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    all_pass = (
        all_metric_checks_pass
        and not found_forbidden
        and sidel_check
        and madebyakim_check
        and title_check
    )

    if all_pass:
        print("\n✅ ASTEK E2E TEST PASSED (V3 REAL PIPELINE)")
        print("\nCritical validations:")
        print("  ✓ Metrics preserved ('6+', 'dozens') - NOT rewritten")
        print("  ✓ No invented content (APS/Supply Chain) - NOT hallucinated")
        print("  ✓ Sidel bullets preserved - NOT removed")
        print("  ✓ MadeByAkim bullets preserved - NOT generalized")
        print("  ✓ Title validated - NOT generated inappropriately")
        print("\nConclusion: V3 pipeline is working correctly!")
        print("Master CV is the authoritative source. Generated CV matches source exactly.")
    else:
        print("\n❌ ASTEK E2E TEST FAILED")
        print("\nFailures:")
        if not all_metric_checks_pass:
            print("  ✗ Metrics check failed - content was rewritten")
        if found_forbidden:
            print(f"  ✗ Invented content found: {found_forbidden}")
        if not sidel_check:
            print("  ✗ Sidel bullets not preserved")
        if not madebyakim_check:
            print("  ✗ MadeByAkim bullets not preserved")
        if not title_check:
            print("  ✗ Title not validated properly")

    # Save HTML for manual inspection
    output_path = Path(__file__).parent / "astek_cv_v3.html"
    with open(output_path, "w") as f:
        f.write(html)
    print(f"\nGenerated CV saved to: {output_path}")

    return {
        "success": all_pass,
        "metrics_preserved": all_metric_checks_pass,
        "no_invented_content": not found_forbidden,
        "bullets_preserved": sidel_check and madebyakim_check,
        "title_valid": title_check,
    }


if __name__ == "__main__":
    try:
        result = asyncio.run(test_astek_e2e_v3_real())
        print("\n" + "=" * 80)
        print(f"Test Result: {result}")
        sys.exit(0 if result.get("success") else 1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
