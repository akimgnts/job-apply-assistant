"""Tests for job_ingestion_service — URL extraction + text ingestion."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.job_ingestion_service import is_url, clean_job_text, ingest_job_input


# ---------------------------------------------------------------------------
# is_url
# ---------------------------------------------------------------------------

def test_is_url_http():
    assert is_url("http://example.com") is True

def test_is_url_https():
    assert is_url("https://recrutement.bpce.fr/job/some-offer") is True

def test_is_url_plain_text():
    assert is_url("Nous recherchons un data analyst...") is False

def test_is_url_ftp_rejected():
    assert is_url("ftp://example.com") is False

def test_is_url_empty():
    assert is_url("") is False

def test_is_url_whitespace_stripped():
    assert is_url("  https://example.com  ") is True


# ---------------------------------------------------------------------------
# clean_job_text
# ---------------------------------------------------------------------------

def test_clean_removes_cookie_banner_lines():
    text = "Nous recherchons un ingénieur.\nAccept all cookies\nPoste basé à Paris."
    result = clean_job_text(text)
    assert "Accept all cookies" not in result
    assert "ingénieur" in result

def test_clean_keeps_linkedin_mentions():
    text = "Retrouvez-nous sur LinkedIn pour plus d'infos sur notre culture."
    result = clean_job_text(text)
    assert "LinkedIn" in result

def test_clean_keeps_contact_section():
    text = "Contact : rh@entreprise.fr pour postuler."
    result = clean_job_text(text)
    assert "Contact" in result

def test_clean_normalizes_spaces():
    text = "Mission  principale :   analyser   les  données."
    result = clean_job_text(text)
    assert "  " not in result

def test_clean_empty_string():
    assert clean_job_text("") == ""

def test_clean_keeps_home_and_about():
    text = "Notre entreprise est basée à Paris.\nAbout us: leader en fintech.\nHome office possible."
    result = clean_job_text(text)
    assert "About us" in result
    assert "Home office" in result


# ---------------------------------------------------------------------------
# ingest_job_input — plain text
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_plain_text():
    offer = "Nous recherchons un Data Analyst expérimenté pour rejoindre notre équipe."
    result = await ingest_job_input(offer)
    assert result["source_type"] == "text"
    assert result["extraction_success"] is True
    assert result["clean_text"] == offer
    assert result["error"] is None
    assert result["source_url"] is None

@pytest.mark.asyncio
async def test_ingest_plain_text_whitespace():
    offer = "  Offre d'emploi Data Engineer.  "
    result = await ingest_job_input(offer)
    assert result["source_type"] == "text"
    assert result["clean_text"] == "Offre d'emploi Data Engineer."


# ---------------------------------------------------------------------------
# ingest_job_input — URL extraction (mocked HTTP)
# ---------------------------------------------------------------------------

SAMPLE_HTML = """
<html><head><title>Data Analyst - BPCE</title></head>
<body>
<nav>Menu Home About</nav>
<article>
<h1>Data &amp; Process Mining Mission Lead (F/H)</h1>
<p>Within the Information Systems Division of the BPCE group,
you join the Data &amp; Analytics team.</p>
<h2>Main responsibilities</h2>
<ul>
<li>Analyze business processes using Process Mining tools (Celonis).</li>
<li>Produce dashboards and analytical reports.</li>
<li>Collaborate with business teams to identify improvement areas.</li>
<li>Present results to stakeholders.</li>
</ul>
<h2>Required profile</h2>
<ul>
<li>Master degree in Data Science, Computer Science or equivalent.</li>
<li>Experience with SQL, Python, and BI tools (Power BI, Tableau).</li>
<li>Knowledge of Agile methodologies.</li>
</ul>
<p>Position based in Paris. Permanent contract.</p>
</article>
<footer>Copyright BPCE 2024</footer>
</body></html>
""".encode("utf-8")

@pytest.mark.asyncio
async def test_ingest_url_success():
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.data = SAMPLE_HTML

    with patch("app.services.job_ingestion_service.urllib3.PoolManager") as MockPool:
        MockPool.return_value.request.return_value = mock_response
        result = await ingest_job_input("https://recrutement.bpce.fr/job/chargee-de-mission-data-et-process-mining-f-h")

    assert result["source_type"] == "url"
    assert result["extraction_success"] is True
    assert result["error"] is None
    assert len(result["clean_text"]) >= 100
    assert "Process Mining" in result["clean_text"] or "Celonis" in result["clean_text"] or "Data" in result["clean_text"]

@pytest.mark.asyncio
async def test_ingest_url_http_403():
    mock_response = MagicMock()
    mock_response.status = 403
    mock_response.data = b"Forbidden"

    with patch("app.services.job_ingestion_service.urllib3.PoolManager") as MockPool:
        MockPool.return_value.request.return_value = mock_response
        result = await ingest_job_input("https://recrutement.bpce.fr/job/some-offer")

    assert result["source_type"] == "url"
    assert result["extraction_success"] is False
    assert "403" in result["error"]

@pytest.mark.asyncio
async def test_ingest_url_empty_html():
    """JS-rendered page: server returns a shell HTML with no content."""
    empty_html = b"<html><body><div id='app'></div></body></html>"
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.data = empty_html

    with patch("app.services.job_ingestion_service.urllib3.PoolManager") as MockPool:
        MockPool.return_value.request.return_value = mock_response
        result = await ingest_job_input("https://recrutement.bpce.fr/job/some-offer")

    assert result["extraction_success"] is False
    assert result["error"] is not None

@pytest.mark.asyncio
async def test_ingest_url_network_error():
    with patch("app.services.job_ingestion_service.urllib3.PoolManager") as MockPool:
        MockPool.return_value.request.side_effect = Exception("Connection timed out")
        result = await ingest_job_input("https://recrutement.bpce.fr/job/some-offer")

    assert result["extraction_success"] is False
    assert "timed out" in result["error"]

@pytest.mark.asyncio
async def test_ingest_url_uses_correct_headers():
    """Verify complete User-Agent and headers are sent."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.data = SAMPLE_HTML

    with patch("app.services.job_ingestion_service.urllib3.PoolManager") as MockPool:
        mock_pool = MockPool.return_value
        mock_pool.request.return_value = mock_response
        await ingest_job_input("https://example.com/job/offer")

        call_kwargs = mock_pool.request.call_args
        headers = call_kwargs[1]["headers"] if call_kwargs[1] else call_kwargs[0][2]
        ua = headers["User-Agent"]

    assert "Chrome/120" in ua
    assert "KHTML, like Gecko" in ua  # complete UA, not truncated
