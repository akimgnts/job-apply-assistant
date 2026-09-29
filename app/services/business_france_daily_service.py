"""Daily Business France radar for the Job Apply Assistant dashboard."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable
from urllib.parse import parse_qs, quote_plus, urlparse

import aiohttp


API_URL = "https://civiweb-api-prd.azurewebsites.net/api/Offers/search"


@dataclass
class ExternalAvailability:
    status: str
    official: list[dict[str, Any]] = field(default_factory=list)
    job_boards: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    candidates: list[dict[str, Any]] = field(default_factory=list)


class BusinessFranceApiProvider:
    """Fetch raw offers from the public Business France VIE API."""

    def __init__(self, api_key: str | None = None, limit: int = 100, max_offers: int = 1000):
        self.api_key = api_key if api_key is not None else os.getenv("BUSINESS_FRANCE_VIE_API_KEY", "")
        self.limit = limit
        self.max_offers = max_offers
        self.scan_limited = False

    async def fetch_offers(self) -> list[dict[str, Any]]:
        if not self.api_key:
            raise RuntimeError("BUSINESS_FRANCE_VIE_API_KEY not set")

        headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}
        offers: list[dict[str, Any]] = []
        skip = 0
        self.scan_limited = False

        async with aiohttp.ClientSession() as session:
            while len(offers) < self.max_offers:
                payload = {
                    "limit": min(self.limit, self.max_offers - len(offers)),
                    "skip": skip,
                    "query": None,
                    "teletravail": ["0"],
                    "porteEnv": ["0"],
                    "activitySectorId": [],
                    "companiesSizes": [],
                    "countriesIds": [],
                    "entreprisesIds": [0],
                    "geographicZones": [],
                    "missionStartDate": None,
                    "missionsDurations": [],
                    "missionsTypesIds": [],
                    "specializationsIds": [],
                    "studiesLevelId": [],
                }
                async with session.post(API_URL, headers=headers, json=payload, timeout=25) as response:
                    if response.status != 200:
                        body = await response.text()
                        raise RuntimeError(f"Business France VIE returned {response.status}: {body[:200]}")
                    data = await response.json()

                if not isinstance(data, dict) or not isinstance(data.get("result"), list):
                    raise RuntimeError("Business France VIE returned an invalid response")
                batch = data["result"]
                if any(not isinstance(item, dict) for item in batch):
                    raise RuntimeError("Business France VIE returned an invalid response")
                if not batch:
                    break
                offers.extend(batch)
                if len(batch) < payload["limit"]:
                    break
                skip += len(batch)
            else:
                self.scan_limited = True

        return offers


def _date_part(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    match = re.match(r"\d{4}-\d{2}-\d{2}", text)
    return match.group(0) if match else None


def filter_offers_by_broadcast_date(offers: Iterable[dict[str, Any]], requested_date: str) -> list[dict[str, Any]]:
    """Keep offers whose Business France broadcast start date matches requested_date."""
    return [offer for offer in offers if _date_part(offer.get("startBroadcastDate")) == requested_date]


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_business_france_offer(offer: dict[str, Any]) -> dict[str, Any]:
    offer_id = offer.get("id")
    source_url = f"https://mon-vie-via.businessfrance.fr/offres/{offer_id}" if offer_id else None
    description = _clean(offer.get("missionDescription")) or ""
    profile = _clean(offer.get("missionProfile")) or ""
    return {
        "id": offer_id,
        "title": _clean(offer.get("missionTitle")) or "Offre VIE",
        "company": _clean(offer.get("organizationName")) or "Entreprise inconnue",
        "city": _clean(offer.get("cityName")),
        "country": _clean(offer.get("countryName")),
        "business_france_url": source_url,
        "broadcast_date": _clean(offer.get("startBroadcastDate")),
        "created_at_source": _clean(offer.get("creationDate")),
        "contact": {
            "name": _clean(offer.get("contactName")),
            "email": _clean(offer.get("contactEmail")),
            "source": "business_france",
            "source_url": source_url,
        },
        "description": description,
        "profile": profile,
        "description_excerpt": description[:360],
        "profile_excerpt": profile[:280],
        "raw": offer,
    }


STRONG_KEYWORDS = {
    "Business analysis": ["business analyst", "moa", "requirements", "user stories", "besoins métier", "recueil des besoins"],
    "Data analysis": ["data analyst", "data analysis", "analyse de données", "data"],
    "Power BI": ["power bi", "bi", "dashboard", "tableau de bord"],
    "SQL": ["sql"],
    "Python": ["python"],
    "AI / automation": ["ai", "ia", "automation", "automatisation", "genai", "agent"],
    "KPI / reporting": ["kpi", "reporting", "indicateurs"],
    "Process improvement": ["process", "workflow", "amélioration", "optimisation"],
    "ERP / CRM": ["erp", "crm", "salesforce", "hubspot", "hris", "systèmes d'information"],
}

MEDIUM_KEYWORDS = {
    "Project / PMO": ["project manager", "pmo", "chef de projet", "coordination"],
    "Product owner": ["product owner", "product manager", "roadmap"],
    "Digital transformation": ["digital transformation", "transformation digitale", "change management"],
    "Supply chain": ["supply chain", "logistique", "operations"],
    "Finance transformation": ["finance transformation", "contrôle de gestion", "financial reporting"],
}

PENALTIES = {
    "Domaine pharmaceutique / médical trop spécialisé": ["pharma", "pharmaceutique", "gmp", "laboratoire médical", "medical device", "validation de lots"],
    "Poste développeur pur": ["full stack", "backend developer", "frontend developer", "devops", "kubernetes", "java developer"],
    "Ingénierie industrielle pure": ["procédés", "mécanique", "industrialisation", "production line", "maintenance industrielle"],
    "Finance pure / M&A": ["m&a", "private equity", "investment banking", "trading", "actuarial"],
    "Achats sans angle data/process": ["procurement", "sourcing", "acheteur"] ,
}


def _matches_keyword(text: str, keyword: str) -> bool:
    # Acronyms such as IA, AI and BI must not match commercial, retail or bilan.
    if len(keyword) <= 3:
        return re.search(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)", text) is not None
    return keyword in text


def score_offer_for_akim(offer: dict[str, Any]) -> dict[str, Any]:
    text = " ".join([
        offer.get("title") or "",
        offer.get("description") or "",
        offer.get("profile") or "",
        offer.get("company") or "",
    ]).lower()

    score = 35
    reasons: list[str] = []
    blockers: list[str] = []

    for label, keywords in STRONG_KEYWORDS.items():
        if any(_matches_keyword(text, keyword) for keyword in keywords):
            score += 8
            reasons.append(label)

    for label, keywords in MEDIUM_KEYWORDS.items():
        if any(_matches_keyword(text, keyword) for keyword in keywords):
            score += 4
            reasons.append(label)

    for label, keywords in PENALTIES.items():
        if any(_matches_keyword(text, keyword) for keyword in keywords):
            score -= 18
            blockers.append(label)

    if offer.get("contact", {}).get("email"):
        score += 3
        reasons.append("Contact direct publié")

    score = max(0, min(100, score))
    if score >= 78 and not blockers:
        priority = "top"
    elif score >= 58:
        priority = "exploitable"
    else:
        priority = "ignore"

    enriched = dict(offer)
    enriched.update({
        "match_score": score,
        "priority": priority,
        "match_reasons": reasons[:8],
        "blockers": blockers,
    })
    return enriched


def _company_domain_guess(company: str) -> str | None:
    words = re.sub(r"[^a-zA-Z0-9 ]", " ", company.lower()).split()
    stop = {"france", "group", "groupe", "sas", "sa", "ltd", "inc", "nord"}
    words = [word for word in words if word not in stop]
    if not words:
        return None
    return words[0]


class _SearchLinksParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.href: str | None = None
        self.label: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and "result__a" in (values.get("class") or "").split():
            self.href = values.get("href")
            self.label = []

    def handle_data(self, data):
        if self.href is not None:
            self.label.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, "".join(self.label)))
            self.href = None


def _candidate_url(href: str) -> str | None:
    parsed = urlparse("https:" + href if href.startswith("//") else href)
    if parsed.hostname in {"duckduckgo.com", "www.duckduckgo.com"}:
        href = parse_qs(parsed.query).get("uddg", [""])[0]
        parsed = urlparse(href)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        return None
    if parsed.hostname.endswith("businessfrance.fr"):
        return None
    # Search and category pages are not individual postings.
    if re.search(r"/(?:search|jobs/search|jobs|careers)/?$", parsed.path, re.I):
        return None
    if any(key in parse_qs(parsed.query) for key in {"q", "query", "keywords"}):
        return None
    return parsed.geturl()


async def verify_external_job_boards(offer: dict[str, Any]) -> ExternalAvailability:
    """Find sourced external candidates; snippets never establish availability."""
    title = offer.get("title") or ""
    company = offer.get("company") or ""
    query = quote_plus(f'"{title}" "{company}" job')
    url = f"https://duckduckgo.com/html/?q={query}"
    candidates: list[dict[str, Any]] = []
    boards: list[dict[str, Any]] = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12) as response:
                if response.status != 200:
                    return ExternalAvailability(status="error", notes=f"Search returned HTTP {response.status}")
                html = await response.text()
    except Exception as exc:  # pragma: no cover - network-dependent fallback
        return ExternalAvailability(status="error", notes=str(exc))

    parser = _SearchLinksParser()
    parser.feed(html)
    domain_hint = _company_domain_guess(company)
    title_terms = [term for term in re.sub(r"[^a-zA-Z0-9 ]", " ", title.lower()).split() if len(term) > 3][:4]
    company_term = (domain_hint or company.lower()).split()[0] if company else ""

    seen = set()
    for href, label in parser.links[:8]:
        href = _candidate_url(href)
        if not href or href in seen:
            continue
        seen.add(href)
        lower = f"{href} {label}".lower()
        title_match = sum(1 for term in title_terms if term in lower) >= max(1, min(2, len(title_terms)))
        company_match = bool(company_term and company_term in lower)
        if not (title_match and company_match):
            continue
        item = {"label": label[:90], "url": href, "source": "duckduckgo", "source_url": url, "verified": False}
        host = urlparse(href).hostname or ""
        board_domains = {"linkedin.com", "indeed.com", "indeed.fr", "glassdoor.com", "glassdoor.fr", "welcometothejungle.com"}
        if any(host == domain or host.endswith("." + domain) for domain in board_domains):
            boards.append(item)
        else:
            candidates.append(item)

    if candidates or boards:
        return ExternalAvailability(
            status="candidate", candidates=candidates, job_boards=boards,
            notes="Search candidates only: posting availability and official company ownership are not verified.",
        )
    return ExternalAvailability(status="not_found", notes="No reliable external match found")


class BusinessFranceDailyService:
    def __init__(
        self,
        provider: BusinessFranceApiProvider | Any | None = None,
        external_verifier: Callable[[dict[str, Any]], Awaitable[ExternalAvailability]] | None = None,
        cache_dir: str | Path = "outputs",
    ):
        self.provider = provider or BusinessFranceApiProvider()
        self.external_verifier = external_verifier or verify_external_job_boards
        self.cache_dir = Path(cache_dir)

    def _cache_file(self, requested_date: str) -> Path:
        return self.cache_dir / f"business_france_{requested_date}" / "daily_offers.json"

    def _read_cache(self, cache_file: Path, requested_date: str) -> dict[str, Any] | None:
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if isinstance(cached, dict) and cached.get("date") == requested_date and isinstance(cached.get("offers"), list):
                if any(not isinstance(offer, dict) for offer in cached["offers"]):
                    return None
                if cached.get("cache_schema_version") != 2:
                    migrated = []
                    for offer in cached["offers"]:
                        availability = offer.get("external_availability") or asdict(ExternalAvailability(status="not_checked"))
                        if availability.get("status") in {"found", "candidate"}:
                            candidates = availability.get("candidates", []) + availability.get("official", [])
                            availability = {
                                **availability, "status": "candidate", "official": [],
                                "candidates": [{**item, "verified": False, "source": "legacy_search_cache"} for item in candidates],
                                "job_boards": [{**item, "verified": False, "source": "legacy_search_cache"} for item in availability.get("job_boards", [])],
                                "notes": "Legacy search candidates; availability and official ownership were not verified.",
                            }
                        normalized = normalize_business_france_offer(offer["raw"]) if isinstance(offer.get("raw"), dict) else offer
                        migrated.append({**score_offer_for_akim(normalized), "external_availability": availability})
                    cached["offers"] = sorted(migrated, key=lambda offer: offer["match_score"], reverse=True)
                    cached["cache_schema_version"] = 2
                return cached
        except (OSError, ValueError):
            pass
        return None

    def _write_cache(self, cache_file: Path, result: dict[str, Any]) -> None:
        temporary = None
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=cache_file.parent, delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(result, handle, ensure_ascii=False, indent=2)
            temporary.replace(cache_file)
        except OSError as exc:
            result["cache_error"] = f"Could not save daily cache: {exc}"
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    async def _check_external(self, offers: list[dict[str, Any]]) -> None:
        for offer in offers:
            if offer["priority"] in {"top", "exploitable"}:
                try:
                    availability = await self.external_verifier(offer)
                except Exception as exc:
                    availability = ExternalAvailability(status="error", notes=str(exc) or type(exc).__name__)
                offer["external_availability"] = asdict(availability)

    async def get_daily_offers(self, requested_date: str | None = None, verify_external: bool = True, use_cache: bool = True) -> dict[str, Any]:
        requested_date = requested_date or date.today().isoformat()
        try:
            if date.fromisoformat(requested_date).isoformat() != requested_date:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("date must be a valid calendar date in YYYY-MM-DD format") from None
        cache_file = self._cache_file(requested_date)
        cached = self._read_cache(cache_file, requested_date)
        if use_cache and cached is not None:
            if verify_external and not cached.get("verified_external"):
                await self._check_external(cached["offers"])
                cached["verified_external"] = True
                self._write_cache(cache_file, cached)
            return {**cached, "cached": True, "stale": False}

        try:
            raw_offers = await self.provider.fetch_offers()
        except (RuntimeError, aiohttp.ClientError, TimeoutError, ValueError) as exc:
            error = f"Business France daily offers unavailable: {str(exc) or type(exc).__name__}"
            if cached is not None:
                return {**cached, "cached": True, "stale": True, "error": error}
            raise RuntimeError(error) from exc
        daily_raw = filter_offers_by_broadcast_date(raw_offers, requested_date)
        offers = [score_offer_for_akim(normalize_business_france_offer(offer)) for offer in daily_raw]
        offers.sort(key=lambda item: item["match_score"], reverse=True)

        for offer in offers:
            offer["external_availability"] = asdict(ExternalAvailability(status="not_checked"))
        if verify_external:
            await self._check_external(offers)

        result = {
            "date": requested_date,
            "source": "business_france",
            "total": len(offers),
            "verified_external": verify_external,
            "offers": offers,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "cached": False,
            "stale": False,
            "cache_schema_version": 2,
            "partial": bool(getattr(self.provider, "scan_limited", False)),
            "source_scan_limit": getattr(self.provider, "max_offers", None),
        }
        if result["partial"]:
            result["warning"] = f"Source scan limited to {result['source_scan_limit']} offers; additional offers may exist for this date."

        self._write_cache(cache_file, result)
        return result
