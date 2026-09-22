import asyncio
from app.services.business_france_vie_adapter import BusinessFranceVieAdapter
from app.models.job_source_adapter import DiscoveredJobUrl


def test_business_france_urls_use_plural_offres():
    async def scenario():
        adapter = BusinessFranceVieAdapter()
        discovered = DiscoveredJobUrl(url='https://mon-vie-via.businessfrance.fr/offres/245336', metadata={
        'title': 'Data Analyst',
        'company': 'ACME',
        'city': 'Brussels',
        'duration': 12,
        'offer_id': 245336,
        'source': 'business_france_vie',
    })

        extracted = await adapter.extract_job(discovered)
        normalized = await adapter.normalize_job(extracted)

        assert extracted['source_url'] == 'https://mon-vie-via.businessfrance.fr/offres/245336'
        assert normalized.job_url == 'https://mon-vie-via.businessfrance.fr/offres/245336'
    asyncio.run(scenario())


def test_business_france_extracts_contact_metadata_when_available():
    async def scenario():
        adapter = BusinessFranceVieAdapter()
        source = {
        'id': 245336,
        'missionTitle': 'Data Analyst',
        'organizationName': 'ACME',
        'contactFirstName': 'Marie',
        'contactLastName': 'Durand',
        'contactJobTitle': 'Chargée de recrutement',
        'contactEmail': 'marie.durand@example.org',
    }

        contact = adapter.extract_contact(source, 'https://mon-vie-via.businessfrance.fr/offres/245336')
        discovered = DiscoveredJobUrl(url='https://mon-vie-via.businessfrance.fr/offres/245336', metadata={
        'title': 'Data Analyst',
        'company': 'ACME',
        'offer_id': 245336,
        'contacts': [contact],
    })
        normalized = await adapter.normalize_job(await adapter.extract_job(discovered))

        assert contact == {
        'contact_name': 'Marie Durand',
        'role_raw': 'Chargée de recrutement',
        'email': 'marie.durand@example.org',
        'source_url': 'https://mon-vie-via.businessfrance.fr/offres/245336',
        'data_source': 'business_france_vie',
        'verification_status': 'pending',
    }
        assert normalized.contacts == [contact]
    asyncio.run(scenario())


def test_publication_date_survives_normalization():
    async def scenario():
        adapter = BusinessFranceVieAdapter()
        item = DiscoveredJobUrl(url='https://example.org/1', metadata={'title':'Analyst','company':'Acme','posted_date':'2026-09-22T00:00:00'})
        result = await adapter.normalize_job(await adapter.extract_job(item))
        assert result.posted_date.isoformat() == '2026-09-22T00:00:00'
    asyncio.run(scenario())
