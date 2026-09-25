import asyncio
from datetime import datetime, timezone

from app.services.apec_api_adapter import ApecAdapter


def result(number, title, published):
    return {
        "numeroOffre": number,
        "intitule": title,
        "nomCommercial": "Acme",
        "lieuTexte": "Paris - 75",
        "texteOffre": "SQL Python Power BI",
        "datePublication": published,
        "dateValidation": published,
        "typeContrat": 101888,
    }


def test_normalize_api_result_uses_publication_date_and_public_url():
    raw = result("179465152W", "Data Analyst F/H", "2026-09-22T20:45:14.000+0000")

    normalized = ApecAdapter.normalize_result(raw)

    assert normalized.job_title == "Data Analyst F/H"
    assert normalized.company_name == "Acme"
    assert normalized.source == "apec"
    assert normalized.external_job_id == "179465152W"
    assert normalized.posted_date == datetime(2026, 9, 22, 20, 45, 14)
    assert normalized.job_url.endswith("/detail-offre/179465152W")
    assert normalized.raw_text == "Lieu: Paris - 75\n\nSQL Python Power BI"


def test_should_stop_after_oldest_recent_window_when_dates_are_sorted():
    now = datetime(2026, 9, 22, 21, tzinfo=timezone.utc)
    recent = result("1W", "Data Analyst", "2026-09-22T20:00:00.000+0000")
    old = result("2W", "Data Analyst", "2026-09-20T20:59:00.000+0000")

    assert ApecAdapter.window_reached(
        [recent, old], now=now, date_field="datePublication", window_hours=48
    ) is True


def test_unsorted_or_missing_dates_disable_early_stop():
    now = datetime(2026, 9, 22, 21, tzinfo=timezone.utc)
    old = result("1W", "Data Analyst", "2026-09-20T20:59:00.000+0000")
    recent = result("2W", "Data Analyst", "2026-09-22T20:00:00.000+0000")
    missing = result("3W", "Data Analyst", None)
    missing.pop("datePublication")

    assert ApecAdapter.dates_sorted([old, recent], "datePublication") is False
    assert ApecAdapter.dates_sorted([missing], "datePublication") is False
    assert ApecAdapter.window_reached([old, recent], now=now, date_field="datePublication", window_hours=48) is True


def test_discover_marks_old_results_and_stops_when_window_is_reached():
    class FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def json(self):
            return {
                "totalCount": 3,
                "resultats": [
                    result("1W", "Data Analyst", "2026-09-22T20:00:00.000+0000"),
                    result("2W", "Data Engineer", "2026-09-20T20:59:00.000+0000"),
                ],
            }

    class FakeSession:
        def __init__(self):
            self.calls = []

        def post(self, url, json, headers=None, timeout=None):
            self.calls.append(json)
            return FakeResponse()

    adapter = ApecAdapter(session=FakeSession())
    discovered = asyncio.run(adapter.discover_jobs({
        "search_terms": "data",
        "now": datetime(2026, 9, 22, 21, tzinfo=timezone.utc),
        "window_hours": 48,
        "page_size": 2,
    }))

    assert [item.metadata["apec_id"] for item in discovered] == ["1W"]
    assert len(adapter.session.calls) == 1


def test_discovery_filters_every_page_to_ile_de_france():
    class FakeResponse:
        status = 200

        def __init__(self, number):
            self.number = number

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def json(self, **kwargs):
            return {
                "totalCount": 2,
                "resultats": [result(self.number, "Data Analyst", "2026-09-22T20:00:00.000+0000")],
            }

    class FakeSession:
        def __init__(self):
            self.calls = []

        def post(self, url, json, **kwargs):
            self.calls.append(json)
            return FakeResponse(str(len(self.calls)))

    for custom_payload in (None, {"lieux": [], "typesContrat": [101888]}):
        session = FakeSession()
        adapter = ApecAdapter(session=session)
        discovered = asyncio.run(adapter.discover_jobs({
            "search_terms": "data",
            "now": datetime(2026, 9, 22, 21, tzinfo=timezone.utc),
            "page_size": 1,
            "payload": custom_payload,
        }))

        assert len(discovered) == 2
        assert [call["pagination"]["startIndex"] for call in session.calls] == [0, 1]
        assert all(call["lieux"] == [711] for call in session.calls)
        assert all(call["motsCles"] == "data" for call in session.calls)
        if custom_payload is not None:
            assert custom_payload["lieux"] == []
            assert all(call["typesContrat"] == [101888] for call in session.calls)
