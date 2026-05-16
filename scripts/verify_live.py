#!/usr/bin/env python3
"""Live HTTP verification of companies.yml against the inclusion standard.

Probes each entry's careers_url and every ATS slug against the provider's
public job-board endpoint. Reports per-company status (pass/warn/fail) with
the failing rule, plus a summary. Designed to run nightly out-of-band; not
suitable as a blocking PR check at the current scale (1600+ entries).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import httpx
import yaml


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "companies.yml"

# Use a current Chrome UA. Many enterprise CDNs (Cloudflare, Akamai) reflexively
# 403 obvious bot UAs even on public careers pages, which produces false
# positives. The browser UA gets through; we still identify ourselves in the
# from-header below.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
FROM_HEADER = "awesome-hiring-companies-verify@users.noreply.github.com"
DEFAULT_TIMEOUT = 15.0
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_CONCURRENCY = 20
DEFAULT_RETRIES = 1

# Per-provider candidate URLs. The slug is considered verified if ANY candidate
# returns 200, which keeps us robust against:
#  - Ashby's posting-API being opt-in per customer (many real boards 404 there
#    but the HTML board page works).
#  - Greenhouse's HTML board redirecting to a custom careers domain that
#    Cloudflare 403s for non-residential IPs (but the JSON API still works).
ATS_ENDPOINTS: dict[str, list[str]] = {
    "ashby": [
        "https://jobs.ashbyhq.com/{slug}",
        "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    ],
    "greenhouse": [
        "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        "https://boards.greenhouse.io/{slug}",
    ],
    "lever": [
        "https://api.lever.co/v0/postings/{slug}?mode=json",
        "https://jobs.lever.co/{slug}",
    ],
    "workable": [
        "https://apply.workable.com/{slug}/",
    ],
    "smartrecruiters": [
        "https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        "https://careers.smartrecruiters.com/{slug}",
    ],
}

# Hosts that mean "this domain is for sale / parked / not the company's site".
# A redirect into one of these flips the domain probe from `OK` to `parked`.
PARKING_HOSTS = frozenset({
    "brandbucket.com",
    "sedo.com",
    "afternic.com",
    "hugedomains.com",
    "dan.com",
    "domainmarket.com",
    "buydomains.com",
    "uniregistry.com",
    "namepros.com",
    "squadhelp.com",
    "atom.com",
})

# Providers whose public board has no canonical public probe endpoint
# (SAP SuccessFactors, Recruiterbox, `custom`). For these, the
# `careers_url` check is the real signal — skip the ATS probe instead
# of failing the entry. Workday used to live in this set but moved to
# probe_ats_workday: its value is now required to be
# <tenant>.<pod>.myworkdayjobs.com/<site>, and we hit the cxs API
# directly so the data is actually crawlable.
NO_PROBE_PROVIDERS: frozenset[str] = frozenset({
    "successfactors",
    "recruiterbox",
    "custom",
})

# Body sent to the Workday cxs API. Documented minimum that satisfies
# the endpoint's schema validation; `limit=1` keeps the response cheap.
WORKDAY_PROBE_BODY = {
    "appliedFacets": {},
    "limit": 1,
    "offset": 0,
    "searchText": "",
}


@dataclass
class Probe:
    rule: str
    ok: bool
    detail: str = ""


@dataclass
class Result:
    name: str
    slug: str
    probes: list[Probe] = field(default_factory=list)

    @property
    def status(self) -> str:
        # `fail` is reserved for structural identity failures: the ATS slug
        # doesn't resolve anywhere, or the `domain` field doesn't point to a
        # real company site (DNS-fail or parked at a marketplace). A
        # bot-blocked careers_url (Cloudflare 403, etc.) with a verified ATS
        # slug downgrades to `warn` — humans can still reach the page.
        ats_failed = any(not p.ok and p.rule.startswith("ats:") for p in self.probes)
        domain_dead = any(
            not p.ok and p.rule == "domain_reachable" for p in self.probes
        )
        careers_failed = any(
            not p.ok and p.rule.startswith("careers_url") for p in self.probes
        )
        if ats_failed or domain_dead:
            return "fail"
        if careers_failed:
            return "warn"
        return "pass"


async def fetch(
    client: httpx.AsyncClient, url: str, *, method: str = "GET", retries: int = DEFAULT_RETRIES
) -> httpx.Response | Exception:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await client.request(method, url, follow_redirects=True)
        except (httpx.HTTPError, httpx.InvalidURL, OSError) as exc:
            last_exc = exc
            if attempt < retries:
                await asyncio.sleep(0.5 * (attempt + 1))
    assert last_exc is not None
    return last_exc


def looks_like_login(response: httpx.Response) -> bool:
    # Only treat redirects to a recognized auth host as login-gated. Body-level
    # heuristics (matching "sign in"/"captcha" strings) produced false positives
    # against modern SPA careers pages whose JS bundles mention those tokens.
    final_host = response.url.host or ""
    return any(
        final_host.startswith(token)
        for token in ("login.", "auth.", "accounts.", "sso.", "signin.")
    )


def alternate_careers_urls(domain: str) -> list[str]:
    """Common career-page URL patterns to try when the configured URL fails.

    Catches the typical mistake where a contributor guessed a wrong path or
    subdomain (e.g. /careers vs /jobs, careers.x vs jobs.x). Returns a fixed
    short list — keep this small to avoid blowing the per-entry probe budget.
    """
    if not domain:
        return []
    return [
        f"https://{domain}/careers",
        f"https://{domain}/jobs",
        f"https://www.{domain}/careers",
        f"https://www.{domain}/jobs",
        f"https://careers.{domain}",
        f"https://jobs.{domain}",
    ]


async def _try(client: httpx.AsyncClient, url: str, retries: int) -> tuple[str, int | None]:
    r = await fetch(client, url, retries=retries)
    if isinstance(r, Exception):
        return url, None
    return url, r.status_code


def _normalize_host(host: str) -> str:
    return host.lower().removeprefix("www.")


async def probe_domain(client: httpx.AsyncClient, domain: str, retries: int) -> Probe:
    """Confirm the `domain` field points at a real company site.

    Catches a class of entries where the ATS slug is valid (so careers_url
    works) but the company's primary domain is dead, never-registered, or
    parked at a marketplace — i.e. the inclusion-standard "stable identity:
    canonical name, primary domain" requirement fails. A 4xx/5xx on the
    company's own root is most often anti-bot from this network and is
    treated as reachable; only DNS/SSL failure or a parking-host redirect
    fails the probe.
    """
    if not domain:
        return Probe("domain_reachable", False, "no domain field")
    last: tuple[str, str] | None = None
    soft_errors: list[str] = []
    hard_error_seen = False
    for variant in (f"https://{domain}/", f"https://www.{domain}/"):
        result = await fetch(client, variant, retries=retries)
        if isinstance(result, Exception):
            detail = f"{variant} -> {type(result).__name__}: {result}"
            last = ("err", detail)
            if isinstance(result, httpx.TimeoutException):
                soft_errors.append(detail)
            else:
                hard_error_seen = True
            continue
        host = _normalize_host(result.url.host or "")
        if host in PARKING_HOSTS:
            return Probe("domain_reachable", False, f"{variant} -> parked at {host}")
        if result.status_code < 400:
            return Probe("domain_reachable", True, f"{variant} -> HTTP {result.status_code} ({host})")
        last = ("http", f"{variant} -> HTTP {result.status_code}")
    if last and last[0] == "http":
        return Probe("domain_reachable", True, f"{last[1]} (treating non-DNS error as anti-bot)")
    if soft_errors and not hard_error_seen:
        return Probe(
            "domain_reachable", True,
            f"{soft_errors[-1]} (treating timeout as anti-bot)",
        )
    return Probe("domain_reachable", False, last[1] if last else "no probe attempted")


async def probe_careers_url(
    client: httpx.AsyncClient, url: str, domain: str, retries: int
) -> Probe:
    result = await fetch(client, url, retries=retries)
    if not isinstance(result, Exception) and 200 <= result.status_code < 400:
        if looks_like_login(result):
            return Probe(
                "careers_url_no_login", False,
                f"final URL {result.url} looks login-gated",
            )
        return Probe("careers_url_reachable", True, f"HTTP {result.status_code}")

    # Primary failed. Try alternates derived from the domain. If any succeed,
    # this still counts as `warn` (not pass) so the report flags the entry as
    # needing a careers_url fix — and includes the alternate as a suggestion.
    primary_detail = (
        f"{type(result).__name__}: {result}" if isinstance(result, Exception)
        else f"HTTP {result.status_code}"
    )
    alts = alternate_careers_urls(domain)
    found: list[str] = []
    for alt in alts:
        if alt == url:
            continue
        _, status = await _try(client, alt, retries=0)
        if status and 200 <= status < 400:
            found.append(f"{alt} (HTTP {status})")
    if found:
        return Probe(
            "careers_url_reachable", False,
            f"primary {primary_detail}; SUGGEST: " + ", ".join(found[:3]),
        )
    return Probe("careers_url_reachable", False, primary_detail)


def ats_slug_values(provider_value: str | list[str]) -> list[str]:
    return provider_value if isinstance(provider_value, list) else [provider_value]


async def probe_ats_workday(
    client: httpx.AsyncClient, slug: str, retries: int
) -> Probe:
    """Verify a Workday entry against the cxs API.

    Unlike the other supported ATSes, the value carried in `ats.workday`
    must be the full `<tenant>.<pod>.myworkdayjobs.com/<site>` string —
    the pod (wd1, wd5, wd12, …) and site key vary per tenant and can't
    be derived from the slug. A bare slug fails this probe with a
    pointer to CONTRIBUTING.md → Workday format.
    """
    rule = f"ats:workday:{slug}"
    if "myworkdayjobs.com" not in slug:
        return Probe(
            rule, False,
            f"value must be '<tenant>.<pod>.myworkdayjobs.com/<site>', got {slug!r}. "
            "See CONTRIBUTING.md → Workday format.",
        )
    try:
        host, site = slug.split("/", 1)
    except ValueError:
        return Probe(rule, False, f"missing '/<site>' segment in {slug!r}")
    tenant = host.split(".", 1)[0]
    url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"

    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = await client.request(
                "POST", url, json=WORKDAY_PROBE_BODY, follow_redirects=True,
            )
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            last_exc = exc
            if attempt < retries:
                await asyncio.sleep(0.5 * (attempt + 1))
            continue
        if r.status_code == 200:
            try:
                data = r.json()
            except ValueError:
                return Probe(rule, False, f"HTTP 200 from {url} but body wasn't JSON")
            # Accept any 200 with a jobPostings key, even when empty —
            # an active tenant with zero open roles right now is still
            # a valid entry.
            if "jobPostings" in (data or {}):
                return Probe(rule, True, f"HTTP 200 from {url}")
            return Probe(rule, False, f"HTTP 200 from {url} but no jobPostings field")
        if r.status_code == 422:
            return Probe(
                rule, False,
                f"HTTP 422 from {url} — host exists on this pod but the site "
                "segment is wrong; check the careers-page URL.",
            )
        if r.status_code == 404:
            return Probe(
                rule, False,
                f"HTTP 404 from {url} — wrong pod, wrong tenant, or moved off Workday",
            )
        return Probe(rule, False, f"HTTP {r.status_code} from {url}")

    assert last_exc is not None
    return Probe(rule, False, f"{type(last_exc).__name__}: {last_exc}")


async def probe_ats(
    client: httpx.AsyncClient, provider: str, slug: str, retries: int
) -> Probe:
    if provider == "workday":
        return await probe_ats_workday(client, slug, retries)
    if provider in NO_PROBE_PROVIDERS:
        return Probe(
            f"ats:{provider}:{slug}", True,
            "no public probe endpoint; relying on careers_url",
        )
    candidates = ATS_ENDPOINTS.get(provider)
    if not candidates:
        return Probe(f"ats:{provider}", False, "unknown ATS provider; no endpoint configured")

    attempts: list[str] = []
    for template in candidates:
        url = template.format(slug=slug)
        result = await fetch(client, url, retries=retries)
        if isinstance(result, Exception):
            attempts.append(f"{url} -> {type(result).__name__}")
            continue
        if result.status_code < 400:
            return Probe(
                f"ats:{provider}:{slug}", True, f"HTTP {result.status_code} from {url}"
            )
        attempts.append(f"{url} -> HTTP {result.status_code}")

    return Probe(f"ats:{provider}:{slug}", False, "; ".join(attempts))


async def verify_company(
    client: httpx.AsyncClient,
    company: dict,
    sem: asyncio.Semaphore,
    retries: int,
) -> Result:
    async with sem:
        result = Result(name=company["name"], slug=company["slug"])
        result.probes.append(await probe_domain(client, company.get("domain", ""), retries))
        result.probes.append(
            await probe_careers_url(
                client, company["careers_url"], company.get("domain", ""), retries
            )
        )
        for provider, value in company.get("ats", {}).items():
            for slug in ats_slug_values(value):
                result.probes.append(await probe_ats(client, provider, slug, retries))
        return result


async def run(
    companies: list[dict], concurrency: int, retries: int, timeout: float
) -> list[Result]:
    sem = asyncio.Semaphore(concurrency)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
        "From": FROM_HEADER,
    }
    timeout_obj = httpx.Timeout(timeout, connect=min(timeout, DEFAULT_CONNECT_TIMEOUT))
    async with httpx.AsyncClient(timeout=timeout_obj, headers=headers, http2=False) as client:
        return await asyncio.gather(
            *(verify_company(client, c, sem, retries) for c in companies)
        )


def filter_companies(companies: list[dict], only_slugs: Iterable[str] | None) -> list[dict]:
    if not only_slugs:
        return companies
    keep = set(only_slugs)
    return [c for c in companies if c.get("slug") in keep]


def render_text(results: list[Result]) -> str:
    lines: list[str] = []
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for r in results:
        counts[r.status] += 1
        if r.status == "pass":
            continue
        lines.append(f"[{r.status.upper()}] {r.name} ({r.slug})")
        for p in r.probes:
            if not p.ok:
                lines.append(f"    - {p.rule}: {p.detail}")
    summary = (
        f"\nSummary: {counts['pass']} pass, "
        f"{counts['warn']} warn, {counts['fail']} fail "
        f"(of {len(results)} total)"
    )
    lines.append(summary)
    return "\n".join(lines)


def render_json(results: list[Result]) -> str:
    payload = [
        {
            "name": r.name,
            "slug": r.slug,
            "status": r.status,
            "probes": [
                {"rule": p.rule, "ok": p.ok, "detail": p.detail} for p in r.probes
            ],
        }
        for r in results
    ]
    return json.dumps(payload, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        nargs="*",
        help="Restrict checks to these slugs (used by the diff-scoped PR job).",
    )
    parser.add_argument(
        "--concurrency", type=int, default=DEFAULT_CONCURRENCY,
        help=f"Max concurrent requests (default: {DEFAULT_CONCURRENCY}).",
    )
    parser.add_argument(
        "--retries", type=int, default=DEFAULT_RETRIES,
        help=f"Retries per request on transient errors (default: {DEFAULT_RETRIES}).",
    )
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT,
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT}).",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text",
    )
    parser.add_argument(
        "--fail-on-warn", action="store_true",
        help="Exit non-zero on warn as well as fail (off by default).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with DATA_PATH.open("r", encoding="utf-8") as f:
        companies = yaml.safe_load(f)
    companies = filter_companies(companies, args.only)
    if not companies:
        print("No companies matched filter; nothing to do.", file=sys.stderr)
        return 0

    results = asyncio.run(
        run(companies, args.concurrency, args.retries, args.timeout)
    )

    if args.format == "json":
        print(render_json(results))
    else:
        print(render_text(results))

    has_fail = any(r.status == "fail" for r in results)
    has_warn = any(r.status == "warn" for r in results)
    if has_fail or (args.fail_on_warn and has_warn):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
