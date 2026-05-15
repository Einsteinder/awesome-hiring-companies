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
        # An entry is `fail` only when a structural identity check fails: the
        # ATS slug doesn't resolve, or the careers_url returns a hard 404/DNS
        # error AND the ATS slug also doesn't verify. A bot-blocked careers_url
        # (e.g. Cloudflare 403) with a verified ATS slug downgrades to `warn`,
        # because a human's browser can still reach the page.
        ats_failed = any(not p.ok and p.rule.startswith("ats:") for p in self.probes)
        careers_failed = any(
            not p.ok and p.rule.startswith("careers_url") for p in self.probes
        )
        if ats_failed:
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
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
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


async def probe_ats(
    client: httpx.AsyncClient, provider: str, slug: str, retries: int
) -> Probe:
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
    wanted = set(only_slugs)
    return [c for c in companies if c["slug"] in wanted]


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
