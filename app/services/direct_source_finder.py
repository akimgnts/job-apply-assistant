"""Find a likely direct employer source for a job-board offer."""
from __future__ import annotations

import html
import re
from urllib.parse import quote, unquote, urlparse

import httpx


class DirectSourceFinder:
    SEARCH_URL = "https://html.duckduckgo.com/html/?q={}"
    BOARD_DOMAINS = {"businessfrance.fr", "mon-vie-via.businessfrance.fr", "apec.fr", "linkedin.com", "indeed.com"}

    @classmethod
    async def find(cls, *, company: str, title: str, original_url: str | None = None, limit: int = 5) -> dict:
        query = f'"{company}" "{title}" (jobs OR careers OR recrutement)'
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=True, headers={"User-Agent": "JobApply/1.0"}) as client:
                response = await client.get(cls.SEARCH_URL.format(quote(query)))
                response.raise_for_status()
            return {"query": query, "results": cls._parse_results(response.text, company, title, original_url, limit), "status": "ok"}
        except Exception as exc:
            return {"query": query, "results": [], "status": "error", "error": str(exc)}

    @classmethod
    def _parse_results(cls, body: str, company: str, title: str, original_url: str | None, limit: int) -> list[dict]:
        rows = []
        pattern = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
        original_host = (urlparse(original_url).hostname or "").lower() if original_url else ""
        for raw_url, raw_title in pattern.findall(body):
            url = html.unescape(raw_url)
            match = re.search(r"uddg=([^&]+)", url)
            if match: url = unquote(match.group(1))
            host = (urlparse(url).hostname or "").lower().removeprefix("www.")
            if not host or host == original_host or any(host == d or host.endswith("." + d) for d in cls.BOARD_DOMAINS): continue
            label = html.unescape(re.sub(r"<[^>]+>", "", raw_title).strip())
            score, reasons = cls._score(host, label, url, company, title)
            rows.append({"url": url, "title": label, "domain": host, "confidence": score, "reasons": reasons})
        return sorted(rows, key=lambda item: item["confidence"], reverse=True)[:limit]

    @staticmethod
    def _score(host: str, label: str, url: str, company: str, title: str) -> tuple[int, list[str]]:
        company_tokens = {t for t in re.findall(r"[a-z0-9]+", company.lower()) if len(t) > 2}
        title_tokens = {t for t in re.findall(r"[a-z0-9]+", title.lower()) if len(t) > 2}
        haystack = f"{host} {label} {url}".lower(); reasons=[]; score=20
        if any(t in haystack for t in company_tokens): score += 35; reasons.append("nom de l’entreprise détecté")
        overlap = sum(t in haystack for t in title_tokens)
        if overlap: score += min(30, overlap * 10); reasons.append(f"{overlap} mot(s) du poste retrouvé(s)")
        if any(w in haystack for w in ("career", "careers", "jobs", "recrut", "talent")): score += 15; reasons.append("page carrière ou recrutement détectée")
        return min(score, 100), reasons
