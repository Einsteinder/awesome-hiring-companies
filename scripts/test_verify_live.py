import pytest
import httpx
from unittest.mock import MagicMock, AsyncMock

from verify_live import (
    filter_companies,
    ats_slug_values,
    looks_like_login,
    alternate_careers_urls,
    _normalize_host,
    Result, fetch, probe_domain, probe_careers_url, probe_ats_workday, probe_ats, NO_PROBE_PROVIDERS,
    Probe,
)

def test_filter_companies():
    companies = [
        {"name": "A", "slug": "a"},
        {"name": "B", "slug": "b"},
        {"name": "C", "slug": "c"},
    ]
    assert filter_companies(companies, None) == companies
    assert filter_companies(companies, []) == companies
    assert filter_companies(companies, ["a", "c"]) == [
        {"name": "A", "slug": "a"},
        {"name": "C", "slug": "c"},
    ]
    assert filter_companies(companies, ["d"]) == []

def test_ats_slug_values():
    assert ats_slug_values("slug1") == ["slug1"]
    assert ats_slug_values(["slug1", "slug2"]) == ["slug1", "slug2"]

def test_looks_like_login():
    def mock_response(host):
        resp = MagicMock(spec=httpx.Response)
        url = MagicMock()
        url.host = host
        resp.url = url
        return resp

    assert looks_like_login(mock_response("login.example.com")) is True
    assert looks_like_login(mock_response("auth.example.com")) is True
    assert looks_like_login(mock_response("accounts.google.com")) is True
    assert looks_like_login(mock_response("sso.company.com")) is True
    assert looks_like_login(mock_response("signin.com")) is True
    assert looks_like_login(mock_response("careers.example.com")) is False
    assert looks_like_login(mock_response("jobs.example.com")) is False
    assert looks_like_login(mock_response("")) is False

def test_alternate_careers_urls():
    domain = "example.com"
    alts = alternate_careers_urls(domain)
    assert len(alts) == 6
    assert "https://example.com/careers" in alts
    assert "https://example.com/jobs" in alts
    assert "https://www.example.com/careers" in alts
    assert "https://www.example.com/jobs" in alts
    assert "https://careers.example.com" in alts
    assert "https://jobs.example.com" in alts

    assert alternate_careers_urls("") == []
    assert alternate_careers_urls(None) == []

def test_normalize_host():
    assert _normalize_host("www.example.com") == "example.com"
    assert _normalize_host("example.com") == "example.com"
    assert _normalize_host("WWW.EXAMPLE.COM") == "example.com"
    assert _normalize_host("EXAMPLE.COM") == "example.com"

def test_result_status():
    # Pass
    r_pass = Result("Test", "test")
    r_pass.probes = [
        Probe("domain_reachable", True),
        Probe("careers_url_reachable", True),
        Probe("ats:provider:slug", True)
    ]
    assert r_pass.status == "pass"

    # Warn (careers URL failed but others passed)
    r_warn = Result("Test", "test")
    r_warn.probes = [
        Probe("domain_reachable", True),
        Probe("careers_url_reachable", False),
        Probe("ats:provider:slug", True)
    ]
    assert r_warn.status == "warn"

    # Fail (domain failed)
    r_fail_domain = Result("Test", "test")
    r_fail_domain.probes = [
        Probe("domain_reachable", False),
        Probe("careers_url_reachable", True),
        Probe("ats:provider:slug", True)
    ]
    assert r_fail_domain.status == "fail"

    # Fail (ATS failed)
    r_fail_ats = Result("Test", "test")
    r_fail_ats.probes = [
        Probe("domain_reachable", True),
        Probe("careers_url_reachable", True),
        Probe("ats:provider:slug", False)
    ]
    assert r_fail_ats.status == "fail"

    # Fail (ATS and Domain failed)
    r_fail_both = Result("Test", "test")
    r_fail_both.probes = [
        Probe("domain_reachable", False),
        Probe("careers_url_reachable", True),
        Probe("ats:provider:slug", False)
    ]
    assert r_fail_both.status == "fail"


@pytest.mark.asyncio
async def test_fetch_success():
    client = MagicMock(spec=httpx.AsyncClient)
    expected_response = httpx.Response(200, request=httpx.Request("GET", "https://example.com"))
    client.request = AsyncMock(return_value=expected_response)

    result = await fetch(client, "https://example.com")
    assert result == expected_response
    client.request.assert_awaited_once()

@pytest.mark.asyncio
async def test_fetch_retry_success():
    client = MagicMock(spec=httpx.AsyncClient)
    expected_response = httpx.Response(200, request=httpx.Request("GET", "https://example.com"))

    # Fail first, succeed second
    client.request = AsyncMock(side_effect=[
        httpx.HTTPError("Transient error"),
        expected_response
    ])

    result = await fetch(client, "https://example.com", retries=1)
    assert result == expected_response
    assert client.request.await_count == 2

@pytest.mark.asyncio
async def test_fetch_retry_exhausted():
    client = MagicMock(spec=httpx.AsyncClient)
    client.request = AsyncMock(side_effect=httpx.HTTPError("Persistent error"))

    result = await fetch(client, "https://example.com", retries=1)
    assert isinstance(result, httpx.HTTPError)
    assert client.request.await_count == 2

@pytest.mark.asyncio
async def test_probe_domain_success(mocker):
    client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url.host = "example.com"
    mocker.patch("verify_live.fetch", new_callable=AsyncMock, return_value=mock_resp)

    probe = await probe_domain(client, "example.com", retries=0)
    assert probe.ok is True
    assert probe.rule == "domain_reachable"

@pytest.mark.asyncio
async def test_probe_domain_parked(mocker):
    client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url.host = "brandbucket.com"
    mocker.patch("verify_live.fetch", new_callable=AsyncMock, return_value=mock_resp)

    probe = await probe_domain(client, "example.com", retries=0)
    assert probe.ok is False
    assert "parked" in probe.detail

@pytest.mark.asyncio
async def test_probe_domain_failure(mocker):
    client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.url.host = "example.com"
    mocker.patch("verify_live.fetch", new_callable=AsyncMock, return_value=mock_resp)

    probe = await probe_domain(client, "example.com", retries=0)
    assert probe.ok is True # Treats 4xx as anti-bot
    assert probe.rule == "domain_reachable"

    mocker.patch("verify_live.fetch", new_callable=AsyncMock, return_value=httpx.ConnectError("Connection failed"))
    probe = await probe_domain(client, "example.com", retries=0)
    assert probe.ok is False

@pytest.mark.asyncio
async def test_probe_careers_url_success(mocker):
    client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mocker.patch("verify_live.fetch", new_callable=AsyncMock, return_value=mock_resp)
    mocker.patch("verify_live.looks_like_login", return_value=False)

    probe = await probe_careers_url(client, "https://example.com/careers", "example.com", 0)
    assert probe.ok is True
    assert probe.rule == "careers_url_reachable"

@pytest.mark.asyncio
async def test_probe_careers_url_login(mocker):
    client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://login.example.com"
    mocker.patch("verify_live.fetch", new_callable=AsyncMock, return_value=mock_resp)
    mocker.patch("verify_live.looks_like_login", return_value=True)

    probe = await probe_careers_url(client, "https://example.com/careers", "example.com", 0)
    assert probe.ok is False
    assert probe.rule == "careers_url_no_login"

@pytest.mark.asyncio
async def test_probe_careers_url_fallback(mocker):
    client = MagicMock()
    mocker.patch("verify_live.fetch", new_callable=AsyncMock, return_value=httpx.HTTPError("error"))
    mocker.patch("verify_live._try", new_callable=AsyncMock, side_effect=lambda c, u, retries=0: (u, 200 if "jobs" in u else None))

    probe = await probe_careers_url(client, "https://example.com/careers", "example.com", 0)
    assert probe.ok is False
    assert "SUGGEST" in probe.detail
    assert "https://example.com/jobs" in probe.detail

@pytest.mark.asyncio
async def test_probe_ats_workday(mocker):
    client = MagicMock()

    # Test valid workday format
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"jobPostings": []}
    client.request = AsyncMock(return_value=mock_resp)

    probe = await probe_ats_workday(client, "company.wd1.myworkdayjobs.com/careers", 0)
    assert probe.ok is True

    # Test invalid workday format
    probe = await probe_ats_workday(client, "company", 0)
    assert probe.ok is False
    assert "value must be" in probe.detail

    # Test 404
    mock_resp.status_code = 404
    probe = await probe_ats_workday(client, "company.wd1.myworkdayjobs.com/careers", 0)
    assert probe.ok is False

@pytest.mark.asyncio
async def test_probe_ats(mocker):
    client = MagicMock()

    # Workday routing
    mock_workday = mocker.patch("verify_live.probe_ats_workday", new_callable=AsyncMock, return_value=Probe("ats:workday:test", True))
    probe = await probe_ats(client, "workday", "test", 0)
    assert probe.ok is True
    mock_workday.assert_awaited_once()

    # No probe providers
    for provider in NO_PROBE_PROVIDERS:
        probe = await probe_ats(client, provider, "test", 0)
        assert probe.ok is True
        assert "no public probe endpoint" in probe.detail

    # Valid ATS provider (e.g., lever)
    mock_fetch = mocker.patch("verify_live.fetch", new_callable=AsyncMock)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_fetch.return_value = mock_resp

    probe = await probe_ats(client, "lever", "test", 0)
    assert probe.ok is True
