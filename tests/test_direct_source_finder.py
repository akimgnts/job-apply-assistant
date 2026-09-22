import asyncio
from app.services.direct_source_finder import DirectSourceFinder

def test_parse_results_excludes_job_boards_and_scores_employer_source():
    body = '<a class="result__a" href="https://mon-vie-via.businessfrance.fr/offres/1">Data Analyst</a><a class="result__a" href="https://acme.com/careers/data-analyst">Acme careers — Data Analyst</a>'
    rows = DirectSourceFinder._parse_results(body, 'Acme', 'Data Analyst', 'https://mon-vie-via.businessfrance.fr/offres/1', 5)
    assert len(rows) == 1 and rows[0]['domain'] == 'acme.com' and rows[0]['confidence'] >= 80

def test_find_returns_safe_error_payload(monkeypatch):
    class BrokenClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, *args, **kwargs): raise RuntimeError('offline')
    monkeypatch.setattr('app.services.direct_source_finder.httpx.AsyncClient', lambda **kwargs: BrokenClient())
    result = asyncio.run(DirectSourceFinder.find(company='Acme', title='Data Analyst'))
    assert result['status'] == 'error' and result['results'] == []
