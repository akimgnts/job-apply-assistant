"""URL normalization for deduplication."""

import re
import hashlib
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication.

    Rules:
    - Lowercase scheme + hostname
    - Remove fragment
    - Remove tracking params (utm_*, fbclid, etc.)
    - Keep context params (lang, ref)
    - Remove trailing slash
    """
    parsed = urlparse(url)

    # Lowercase scheme + hostname
    scheme = parsed.scheme.lower()
    netloc = (parsed.hostname or "").lower()
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    # Parse and filter query parameters
    params = parse_qs(parsed.query, keep_blank_values=True)

    TRACKING_PARAMS = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "fbclid",
        "gclid",
        "msclkid",
    }
    KEEP_PARAMS = {"lang", "ref", "country", "filter"}

    filtered_params = {
        k: v
        for k, v in params.items()
        if k not in TRACKING_PARAMS or k in KEEP_PARAMS
    }

    # Reconstruct query string (sorted for consistency)
    new_query = urlencode(filtered_params, doseq=True) if filtered_params else ""

    # Build normalized URL
    normalized = urlunparse(
        (
            scheme,
            netloc,
            parsed.path.rstrip("/").lower(),
            "",  # params (deprecated)
            new_query,
            "",  # fragment (removed)
        )
    )

    return normalized


def url_hash(url: str) -> str:
    """Generate SHA256 hash of normalized URL."""
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are on same domain."""
    parsed1 = urlparse(url1)
    parsed2 = urlparse(url2)
    return parsed1.hostname == parsed2.hostname
