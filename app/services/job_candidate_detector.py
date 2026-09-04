"""Deterministic job page detection via heuristic scoring."""

import re


class JobCandidateDetector:
    """Score pages as probable job listings using deterministic signals."""

    JOB_URL_PATTERNS = [
        r"/job[s]?(?:/|$)",
        r"/career[s]?(?:/|$)",
        r"/position[s]?(?:/|$)",
        r"/vacancies?(?:/|$)",
        r"/opportunities?(?:/|$)",
        r"/opening[s]?(?:/|$)",
        r"/recruit",
        r"/apply(?:/|$)",
    ]

    JOB_TITLE_KEYWORDS = [
        "engineer",
        "analyst",
        "manager",
        "consultant",
        "developer",
        "designer",
        "architect",
        "specialist",
        "coordinator",
        "director",
        "lead",
        "sr.",
        "senior",
        "junior",
        "associate",
    ]

    DESCRIPTION_KEYWORDS = [
        "requirements?",
        "responsibilities?",
        "skills?",
        "experience",
        "qualifications?",
        "about this role",
    ]

    THRESHOLD = 60  # minimum score to consider as job candidate

    @staticmethod
    def score(url: str, html: str, title: str = None) -> dict:
        """Score a page as probable job listing.

        Returns {score: 0-100, signals: {name: bool, ...}, is_candidate: bool}
        """
        signals = {}
        score = 0

        # Signal 1: URL pattern (35 points)
        url_lower = url.lower()
        has_job_pattern = any(
            re.search(pattern, url_lower) for pattern in JobCandidateDetector.JOB_URL_PATTERNS
        )
        signals["url_pattern"] = has_job_pattern
        if has_job_pattern:
            score += 35

        # Signal 2: Schema.org JobPosting (40 points)
        has_schema = "jobposting" in html.lower() or "schema.org" in html.lower()
        signals["jobposting_schema"] = has_schema
        if has_schema:
            score += 40

        # Signal 3: Apply button or action (20 points)
        has_apply = bool(
            re.search(r'<a[^>]*href[^>]*apply', html, re.IGNORECASE)
            or re.search(r'<button[^>]*apply', html, re.IGNORECASE)
            or re.search(r'apply\s+(now|here)', html, re.IGNORECASE)
        )
        signals["apply_button"] = has_apply
        if has_apply:
            score += 20

        # Signal 4: Description markers (15 points)
        has_desc = bool(
            re.search(
                r"(requirements?|responsibilities?|skills?|experience)",
                html,
                re.IGNORECASE,
            )
            and len(html) > 500
        )
        signals["description_markers"] = has_desc
        if has_desc:
            score += 15

        # Signal 5: Title signal (10 points)
        has_title = False
        if title:
            has_title = any(kw in title.lower() for kw in JobCandidateDetector.JOB_TITLE_KEYWORDS)
        signals["title_signal"] = has_title
        if has_title:
            score += 10

        # Signal 6: Content length (5 points)
        text_len = len(re.sub(r"<[^>]+>", "", html))
        is_nontrivial = 400 < text_len < 10000
        signals["content_length"] = is_nontrivial
        if is_nontrivial:
            score += 5

        return {
            "score": min(100, score),
            "signals": signals,
            "is_candidate": score >= JobCandidateDetector.THRESHOLD,
        }
