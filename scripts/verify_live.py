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

USER_AGENT = (
    "Mozilla/5.0 (awesome-hiring-companies-verify/1.0; "
    "+https://github.com/your-org/awesome-hiring-companies)"
)
TIMEOUT = httpx.Timeout(15.0, connect=10.0)
DEFAULT_CONCURRENCY = 20
RETRIES = 1

# Public job-board endpoints. JSON where available (stable + small), HTML for
# providers without an open API. A 200 from these confirms the slug exists.
ATS_ENDPOINTS = {
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "workable": "https://apply.workable.com/{slug}/",
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
        if any(not p.ok for p in self.probes if p.rule != "active_openings"):
            return "fail"
        if any(not p.ok for p in self.probes):
            return "warn"
        return "pass"


async def fetch(
    client: httpx.AsyncClient, url: str, *, method: str = "GET"
) -> httpx.Response | Exception:
    last_exc: Exception | None = None
    for attempt in range(RETRIES + 1):
        try:
            return await client.request(method, url, follow_redirects=True)
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            last_exc = exc
            if attempt < RETRIES:
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


async def probe_careers_url(client: httpx.AsyncClient, url: str) -> Probe:
    result = await fetch(client, url)
    if isinstance(result, Exception):
        return Probe("careers_url_reachable", False, f"{type(result).__name__}: {result}")
    if result.status_code >= 400:
        return Probe("careers_url_reachable", False, f"HTTP {result.status_code}")
    if looks_like_login(result):
        return Probe(
            "careers_url_no_login",
            False,
            f"final URL {result.url} looks login-gated",
        )
    return Probe("careers_url_reachable", True, f"HTTP {result.status_code}")


def ats_slug_values(provider_value: str | list[str]) -> list[str]:
    return provider_value if isinstance(provider_value, list) else [provider_value]


def parse_active_jobs(provider: str, response: httpx.Response) -> int | None:
    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError):
        return None
    if provider == "greenhouse":
        return len(data.get("jobs", []))
    if provider == "lever":
        return len(data) if isinstance(data, list) else None
    if provider == "ashby":
        jobs = data.get("jobs") if isinstance(data, dict) else None
        return len(jobs) if isinstance(jobs, list) else None
    if provider == "workable":
        # Workable endpoint is HTML; 200 already confirms the slug. No count.
        return None
    return None


async def probe_ats(
    client: httpx.AsyncClient, provider: str, slug: str
) -> tuple[Probe, Probe | None]:
    template = ATS_ENDPOINTS.get(provider)
    if template is None:
        return (
            Probe(f"ats:{provider}", False, "unknown ATS provider; no endpoint configured"),
            None,
        )
    url = template.format(slug=slug)
    result = await fetch(client, url)
    if isinstance(result, Exception):
        return Probe(f"ats:{provider}:{slug}", False, f"{type(result).__name__}: {result}"), None
    if result.status_code >= 400:
        return (
            Probe(
                f"ats:{provider}:{slug}",
                False,
                f"HTTP {result.status_code} from {url}",
            ),
            None,
        )

    valid = Probe(f"ats:{provider}:{slug}", True, f"HTTP {result.status_code}")
    job_count = parse_active_jobs(provider, result)
    if job_count is None:
        return valid, None
    return valid, Probe(
        "active_openings",
        job_count > 0,
        f"{job_count} open roles via {provider}",
    )


async def verify_company(
    client: httpx.AsyncClient,
    company: dict,
    sem: asyncio.Semaphore,
) -> Result:
    async with sem:
        result = Result(name=company["name"], slug=company["slug"])
        result.probes.append(await probe_careers_url(client, company["careers_url"]))
        for provider, value in company.get("ats", {}).items():
            for slug in ats_slug_values(value):
                ats_probe, openings_probe = await probe_ats(client, provider, slug)
                result.probes.append(ats_probe)
                if openings_probe is not None:
                    result.probes.append(openings_probe)
        return result


async def run(companies: list[dict], concurrency: int) -> list[Result]:
    sem = asyncio.Semaphore(concurrency)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/html, */*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers, http2=False) as client:
        return await asyncio.gather(
            *(verify_company(client, c, sem) for c in companies)
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

    results = asyncio.run(run(companies, args.concurrency))

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
