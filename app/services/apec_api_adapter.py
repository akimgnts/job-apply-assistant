"""APEC JSON search adapter with a safe recent-window collector.

APEC's public search endpoint is usable without the detail endpoint.  The
detail endpoint is protected intermittently by DataDome, so search results are
the canonical minimum and detail enrichment is best effort.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from app.models.job_source_adapter import DiscoveredJobUrl, JobSourceAdapter, NormalizedJobOffer

logger = logging.getLogger(__name__)

APEC_SEARCH_URL = "https://www.apec.fr/cms/webservices/rechercheOffre"
APEC_DETAIL_PAGE = "https://www.apec.fr/candidat/recherche-emploi.html/emploi/detail-offre/{id}"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://www.apec.fr",
    "Referer": "https://www.apec.fr/candidat/recherche-emploi.html/emploi",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36",
}

BASE_PAYLOAD = {
    "motsCles": "",
    "lieux": [], "fonctions": [], "statutPoste": [], "typesContrat": [],
    "typesConvention": [], "niveauxExperience": [], "secteursActivite": [],
    "typesTeletravail": [], "idsEtablissement": [], "idNomZonesDeplacement": [],
    "positionNumbersExcluded": [], "typeClient": "CADRE",
    "sorts": [{"type": "DATE", "direction": "DESCENDING"}],
    "pagination": {"range": 20, "startIndex": 0},
    "activeFiltre": True,
    "pointGeolocDeReference": {"distance": 0},
}


def parse_apec_date(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(timezone.utc)
    except ValueError:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return None


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip())


class ApecAdapter(JobSourceAdapter):
    source_name = "apec"
    collection_strategy = "api"

    def __init__(self, session=None):
        self.session = session
        self.own_session = session is None
        self.last_run = {"stop_reason": None, "warning": None, "pages": 0, "results": 0}

    async def _ensure_session(self):
        # Production uses stdlib urllib in a worker thread. A session can be
        # injected by tests or by a caller that already owns an HTTP client.
        return None

    async def close(self):
        if self.own_session and self.session:
            await self.session.close()

    @staticmethod
    def dates_sorted(results: list[dict], date_field: str = "datePublication", previous: datetime | None = None) -> bool:
        dates = []
        for item in results:
            parsed = parse_apec_date(item.get(date_field))
            if parsed is None:
                return False
            dates.append(parsed)
        if previous is not None:
            dates.insert(0, previous)
        return all(left >= right for left, right in zip(dates, dates[1:]))

    @staticmethod
    def window_reached(results: list[dict], now: datetime, date_field: str = "datePublication", window_hours: int = 48) -> bool:
        cutoff = now.astimezone(timezone.utc) - timedelta(hours=window_hours)
        dates = [parse_apec_date(item.get(date_field)) for item in results]
        return bool(dates) and all(value is not None for value in dates) and any(value < cutoff for value in dates)

    @staticmethod
    def normalize_result(raw: dict) -> NormalizedJobOffer:
        number = str(raw.get("numeroOffre") or raw.get("id") or "")
        description = raw.get("texteOffre") or ""
        posted = parse_apec_date(raw.get("datePublication"))
        return NormalizedJobOffer(
            job_title=raw.get("intitule") or "Offre APEC",
            company_name=raw.get("nomCommercial") or "Entreprise à préciser",
            job_url=APEC_DETAIL_PAGE.format(id=number),
            source="apec",
            location=raw.get("lieuTexte"),
            # typeContrat is an APEC nomenclature id; keep it out of the
            # canonical string field until a nomenclature endpoint is mapped.
            contract_type=None,
            posted_date=posted.replace(tzinfo=None) if posted else None,
            raw_text=description,
            external_job_id=number,
            required_skills=None,
            description=description,
        )

    async def discover_jobs(self, context: dict) -> list[DiscoveredJobUrl]:
        await self._ensure_session()
        keyword = context.get("search_terms", "")
        if isinstance(keyword, list):
            keyword = " ".join(keyword)
        max_results = int(context.get("max_results", 200))
        page_size = int(context.get("page_size", 20))
        window_hours = int(context.get("window_hours", 48))
        date_field = context.get("date_field", "datePublication")
        now = context.get("now") or datetime.now(timezone.utc)
        now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        cutoff = now.astimezone(timezone.utc) - timedelta(hours=window_hours)
        base = json.loads(json.dumps(context.get("payload") or BASE_PAYLOAD))
        discovered: list[DiscoveredJobUrl] = []
        start = 0
        previous_date = None
        early_stop = True
        stop_reason = "max_reached"

        while len(discovered) < max_results:
            payload = json.loads(json.dumps(base))
            payload["motsCles"] = keyword
            payload["pagination"] = {"range": page_size, "startIndex": start}
            try:
                if self.session is not None:
                    async with self.session.post(APEC_SEARCH_URL, json=payload, headers=HEADERS, timeout=30) as response:
                        status = response.status
                        try:
                            data = await response.json(content_type=None)
                        except TypeError:
                            data = await response.json()
                else:
                    status, body = await asyncio.to_thread(self._urllib_request, "POST", APEC_SEARCH_URL, payload)
                    data = json.loads(body)
                if status != 200:
                    self.last_run.update(stop_reason="http_error", pages=self.last_run["pages"] + 1)
                    raise RuntimeError(f"APEC search returned HTTP {status}")
            except Exception:
                self.last_run.update(stop_reason="http_error", pages=self.last_run["pages"] + 1)
                raise

            self.last_run["pages"] += 1
            results = data.get("resultats") or []
            if not results:
                stop_reason = "window_reached" if discovered else "max_reached"
                break
            page_sorted = self.dates_sorted(results, date_field, previous_date)
            if not page_sorted:
                early_stop = False
                self.last_run["warning"] = f"{date_field} absent ou tri APEC incohérent"

            page_old = False
            for raw in results:
                parsed = parse_apec_date(raw.get(date_field))
                if parsed:
                    previous_date = parsed
                if early_stop and parsed is not None and parsed < cutoff:
                    page_old = True
                    break
                if not raw.get("numeroOffre"):
                    continue
                discovered.append(DiscoveredJobUrl(
                    url=APEC_DETAIL_PAGE.format(id=raw["numeroOffre"]),
                    metadata={"apec_id": raw["numeroOffre"], "title": raw.get("intitule"),
                              "company_name": raw.get("nomCommercial"), "posted_date": raw.get(date_field),
                              "location": raw.get("lieuTexte"), "raw": raw, "new_this_run": True},
                ))
                if len(discovered) >= max_results:
                    break
            if page_old:
                stop_reason = "window_reached"
                break
            start += page_size
            if data.get("totalCount") is not None and start >= int(data["totalCount"]):
                stop_reason = "max_reached"
                break
            await asyncio.sleep(float(context.get("sleep", 0)))

        self.last_run.update(stop_reason=stop_reason, results=len(discovered), early_stop=early_stop)
        return discovered

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        raw = dict(discovered.metadata.get("raw") or {})
        raw.update({"source_url": discovered.url, "apec_id": discovered.metadata.get("apec_id")})
        # Search results are enough to persist a usable offer. Detail HTML is
        # best effort and may be blocked by DataDome.
        if not discovered.metadata.get("enrich_details"):
            return raw
        await self._ensure_session()
        try:
            if self.session is not None:
                async with self.session.get(discovered.url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=20) as response:
                    status = response.status
                    html = await response.text(errors="replace") if status == 200 else ""
            else:
                status, html = await asyncio.to_thread(self._urllib_request, "GET", discovered.url, None)
            if status == 200:
                parser = _TextParser()
                parser.feed(html)
                text = " ".join(parser.parts)
                if len(text) > len(raw.get("texteOffre") or ""):
                    raw["texteOffre"] = text[:20000]
        except Exception as exc:
            logger.info("APEC detail enrichment unavailable for %s: %s", discovered.url, type(exc).__name__)
        return raw

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        return self.normalize_result(extracted)

    @staticmethod
    def _urllib_request(method: str, url: str, payload: dict | None):
        import urllib.error
        import urllib.request
        import ssl

        try:
            import certifi
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ssl_context = ssl.create_default_context()

        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30, context=ssl_context) as response:
                return response.status, response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", "replace")
