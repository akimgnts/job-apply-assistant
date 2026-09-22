# Workspace signal quality

Implement the user's requested separation of preparation and Gmail tracking.

- Dedicated #tracking route, with backwards compatibility for the old applications tracking URL.
- Default history excludes job board alerts and incomplete extracted identities. Review and raw messages remain accessible. Ignored events stay ignored.
- Use Gmail thread IDs and confirmed application associations; avoid merging unrelated roles on employer name alone. Reads no longer create canonical opportunities.
- Prefer sent recipients over incidental employer mentions. Respect manual message classifications. Display sent/received counts and a chronological thread detail.
- Recent radar means published within 48 hours by default, never first discovered within 48 hours. Unknown publication dates remain available with the all-dates filter. Historical offers remain eligible for market analysis.
- Evolution starts with steps and deliverables, followed by sample counts and skill frequency bars. Describe gaps as absent evidence, not proof of absent ability. Link official learning resources when available.
- Contacts show real collected identities, coordinates, sources and verification status. Companies show stored offer/contact counts.

Validation: regression cases for incidental employer mentions, candidate names, ignored events, thread grouping and latest rejection; API tests for read-only listing and owner-scoped thread access; publication freshness tests; career analysis and browser checks. No database migration or historical email deletion.
