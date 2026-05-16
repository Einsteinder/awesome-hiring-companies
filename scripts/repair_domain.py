#!/usr/bin/env python3
"""Propose `domain` field repairs for entries whose primary domain is dead
or parked but whose ATS slug still verifies.

Strategy, in order of confidence:
  1. Look for the slug as a hostname in the ATS posting JSON (job
     descriptions, apply URLs). Most reliable when the company's own
     content references their website.
  2. Try common alternate TLD/prefix patterns for the slug
     (slug.<tld>, get/go/use/try-<slug>.com, etc.), verify reachable.
  3. Cross-check: a candidate "wins" only if its page references the
     ATS board URL or the slug as a hostname. Reduces the risk of
     pointing at a same-named but unrelated business.

Outputs JSON to stdout, one record per repair candidate:
  {slug, current_domain, proposal, confidence, evidence}

Without --apply: report only. With --apply: rewrite data/companies.yml
in place, replacing only the `domain` line of each high-confidence entry.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "companies.yml"

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
TIMEOUT = httpx.Timeout(10.0, connect=8.0)

# JSON endpoints for description scraping. The HTML board pages are React SPAs
# and don't expose the company website in static markup.
POSTING_JSON = {
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
}

# Hostnames that aren't a company's primary domain.
NOISE_HOSTS = {
    "ashbyhq.com", "jobs.ashbyhq.com", "api.ashbyhq.com", "cdn.ashbyprd.com",
    "greenhouse.io", "boards.greenhouse.io", "boards-api.greenhouse.io",
    "job-boards.greenhouse.io",
    "lever.co", "jobs.lever.co", "api.lever.co",
    "workable.com", "apply.workable.com",
    "linkedin.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "youtube.com", "youtu.be", "github.com", "medium.com", "substack.com",
    "google.com", "googleapis.com", "gstatic.com", "googletagmanager.com",
    "fonts.googleapis.com", "schema.org", "cloudfront.net", "cloudflare.com",
    "amazonaws.com", "azure.com", "wikipedia.org", "crunchbase.com",
    "angellist.com", "wellfound.com", "glassdoor.com", "indeed.com",
    "bloomberg.com", "techcrunch.com", "forbes.com", "nytimes.com",
    "wsj.com", "tiktok.com", "discord.gg", "discord.com", "telegram.org",
    "t.me", "reddit.com",
}

PARKING_HOSTS = {
    "brandbucket.com", "sedo.com", "afternic.com", "hugedomains.com",
    "dan.com", "domainmarket.com", "buydomains.com", "uniregistry.com",
    "namepros.com", "squadhelp.com", "atom.com",
}

# Common alternate patterns to try when the slug-on-com domain is dead.
TLD_VARIANTS = [".ai", ".io", ".co", ".dev", ".xyz", ".gg", ".app", ".tech", ".so"]
PREFIX_VARIANTS = ["get", "go", "try", "use", "join", "the"]
SUFFIX_VARIANTS = ["app", "hq", "ai", "io", "co", "labs"]

URL_RE = re.compile(r"https?://[a-zA-Z0-9./?=_&%#:-]+")
SLUG_RE = re.compile(r"^\s*slug:\s*([a-z0-9-]+)\s*$")
DOMAIN_RE = re.compile(r"^\s*domain:\s*")
INDENT_RE = re.compile(r"^(\s*)")


@dataclass
class Proposal:
    slug: str
    name: str
    current_domain: str
    new_domain: str | None
    confidence: str  # "high", "medium", "none"
    evidence: list[str]


def normalize_host(host: str) -> str:
    return host.lower().removeprefix("www.")


def is_noise(host: str) -> bool:
    h = normalize_host(host)
    return h in NOISE_HOSTS or h.endswith(".cloudfront.net") or h.endswith(".amazonaws.com")


def is_parked(host: str) -> bool:
    return normalize_host(host) in PARKING_HOSTS


async def fetch(client: httpx.AsyncClient, url: str) -> httpx.Response | Exception:
    try:
        return await client.get(url, follow_redirects=True)
    except Exception as exc:
        return exc


async def domain_works(
    client: httpx.AsyncClient, domain: str
) -> tuple[bool, str, str | None]:
    """Check whether a candidate domain points at a real, non-parked site.

    Returns (ok, reason, final_host). `final_host` is the post-redirect host
    so callers can detect "redirect to a different brand" (e.g. specter.io
    301→introvert.com — same-named domain, completely different company).
    """
    for variant in (f"https://{domain}/", f"https://www.{domain}/"):
        r = await fetch(client, variant)
        if isinstance(r, Exception):
            continue
        host = normalize_host(r.url.host or "")
        if is_parked(host):
            return False, f"parked at {host}", host
        if r.status_code < 400 or r.status_code in (403, 401):
            return True, f"HTTP {r.status_code} -> {host}", host
    return False, "unreachable", None


def host_is_self(candidate: str, final_host: str) -> bool:
    """The candidate `apex.tld` is considered itself if the final host is the
    same apex (with or without `www.`) — not a redirect to a different brand."""
    c = normalize_host(candidate)
    f = normalize_host(final_host)
    return c == f or f.endswith("." + c)


async def collect_atom_hosts(
    client: httpx.AsyncClient, provider: str, slug: str
) -> list[str]:
    """Pull non-noise hostnames out of the ATS posting JSON."""
    url_tpl = POSTING_JSON.get(provider)
    if not url_tpl:
        return []
    r = await fetch(client, url_tpl.format(slug=slug))
    if isinstance(r, Exception) or r.status_code >= 400:
        return []
    try:
        data = r.json()
    except Exception:
        return []

    text_chunks: list[str] = []
    jobs = data.get("jobs") if isinstance(data, dict) else (data if isinstance(data, list) else [])
    if not jobs:
        return []
    for j in jobs[:15]:  # bound work
        for key in ("descriptionHtml", "descriptionPlain", "content", "description", "additionalPlain"):
            v = j.get(key) if isinstance(j, dict) else None
            if isinstance(v, str):
                text_chunks.append(v)
    blob = " ".join(text_chunks)
    urls = URL_RE.findall(blob)
    hosts: list[str] = []
    seen: set[str] = set()
    for u in urls:
        host = normalize_host(urlparse(u).hostname or "")
        if not host or is_noise(host) or host in seen:
            continue
        seen.add(host)
        hosts.append(host)
    return hosts


SECOND_LEVEL_TLDS = {"co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "co.jp", "co.kr", "com.br"}


def host_base(host: str) -> str:
    """Return the brand portion of a host, accounting for multi-part TLDs.

    `blog.succinct.xyz` -> `succinct`
    `plinth.org.uk`     -> `plinth`   (not `org`)
    `careers.appian.com` -> `appian`
    """
    h = normalize_host(host)
    parts = h.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in SECOND_LEVEL_TLDS:
        return parts[-3]
    if len(parts) >= 2:
        return parts[-2]
    return h


def host_matches_slug(host: str, slug: str, name: str) -> bool:
    """A host plausibly belongs to the company if its brand token matches.

    Requires the host's brand portion to either equal the slug, or be one of
    a small set of brand-extension patterns built around the slug. For short
    slugs (<5 chars) requires exact match, because patterns like
    monaco = mona+co produce too many false positives for short tokens.
    """
    base = host_base(host)
    needle = slug.replace("-", "")
    if not base or not needle:
        return False
    if base == needle:
        return True
    if len(needle) < 5:
        return False  # too risky to apply prefix/suffix patterns here
    PREFIXES = ("get", "go", "try", "use", "join", "the", "my")
    SUFFIXES = ("app", "hq", "ai", "io", "labs", "tech")
    if base.startswith(needle) and base[len(needle):] in SUFFIXES:
        return True
    if base.endswith(needle) and base[:-len(needle)] in PREFIXES:
        return True
    return False


def candidate_tld_variants(slug: str) -> list[str]:
    """Build a small list of likely-correct domain variants for the slug."""
    bare = slug.replace("-", "")
    cands: list[str] = []
    for tld in TLD_VARIANTS:
        cands.append(f"{bare}{tld}")
    for pre in PREFIX_VARIANTS:
        cands.append(f"{pre}{bare}.com")
    for suf in SUFFIX_VARIANTS:
        cands.append(f"{bare}{suf}.com")
    # Hyphenated form too, when slug has dashes
    if "-" in slug:
        for tld in TLD_VARIANTS:
            cands.append(f"{slug}{tld}")
    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


async def page_links_to_ats(
    client: httpx.AsyncClient, host: str, slug: str, providers: Iterable[str]
) -> bool:
    """Strongest cross-check: the candidate site links to *this* ATS board.

    Avoids "slug appears as a keyword" false positives (e.g. "specter" appears
    in random sites' marketing copy). A homepage that links to
    `jobs.ashbyhq.com/<slug>` is overwhelmingly the right company.
    """
    for path in ("/", "/careers", "/careers/", "/jobs", "/jobs/", "/about", "/company"):
        r = await fetch(client, f"https://{host}{path}")
        if isinstance(r, Exception) or r.status_code >= 500:
            continue
        body = r.text[:300000].lower()
        for provider in providers:
            needles = {
                "ashby": f"ashbyhq.com/{slug}",
                "lever": f"lever.co/{slug}",
                "greenhouse": f"greenhouse.io/{slug}",
                "workable": f"workable.com/{slug}",
            }
            needle = needles.get(provider)
            if needle and needle in body:
                return True
    return False


async def gather_ats_candidates(
    client: httpx.AsyncClient, ats: dict
) -> list[tuple[str, str]]:
    """Gather domain candidates from ATS posting JSON."""
    candidates: list[tuple[str, str]] = []
    for provider, value in ats.items():
        slugs = value if isinstance(value, list) else [value]
        for ats_slug in slugs:
            hosts = await collect_atom_hosts(client, provider, ats_slug)
            for host in hosts:
                candidates.append((host, f"{provider}-desc"))
    return candidates


async def evaluate_candidates(
    client: httpx.AsyncClient,
    candidates: list[tuple[str, str]],
    slug: str,
    name: str,
    current: str,
    providers: list[str],
    evidence: list[str],
) -> Proposal | None:
    """Score and verify candidates."""
    seen_hosts: set[str] = set()
    medium_fallback: Proposal | None = None

    for host, source in candidates:
        host_norm = normalize_host(host)
        if host_norm == current.lower() or host_norm in seen_hosts:
            continue
        seen_hosts.add(host_norm)

        ok, why, final_host = await domain_works(client, host_norm)
        if not ok:
            continue

        same_brand = final_host is not None and host_is_self(host_norm, final_host)
        slug_in_host = host_matches_slug(host_norm, slug, name)
        links_to_ats = await page_links_to_ats(client, final_host or host_norm, slug, providers)

        if same_brand and links_to_ats and slug_in_host:
            parts = host_norm.split(".")
            apex = host_norm
            if len(parts) >= 3:
                tail2 = ".".join(parts[-2:])
                if tail2 in SECOND_LEVEL_TLDS:
                    apex = ".".join(parts[-3:])
                else:
                    apex = tail2
            if apex != host_norm:
                apex_ok, _, apex_final = await domain_works(client, apex)
                if apex_ok and apex_final and host_is_self(apex, apex_final):
                    host_norm = apex
            evidence.append(f"{host_norm} ({source}): {why}; same-brand + links-to-ats")
            return Proposal(slug, name, current, host_norm, "high", evidence)

        from_ats = source.endswith("-desc")
        if from_ats and same_brand:
            evidence.append(
                f"{host_norm} ({source}): {why}; "
                f"same-brand={same_brand}, slug-in-host={slug_in_host}, links-to-ats={links_to_ats}"
            )
            if medium_fallback is None:
                medium_fallback = Proposal(slug, name, current, host_norm, "medium", list(evidence))

    return medium_fallback


async def repair_one(
    client: httpx.AsyncClient, company: dict, sem: asyncio.Semaphore
) -> Proposal:
    async with sem:
        slug = company["slug"]
        name = company["name"]
        current = company["domain"]
        evidence: list[str] = []

        # First: is the current domain actually broken? Skip ones that work.
        ok, why, _ = await domain_works(client, current)
        if ok:
            return Proposal(slug, name, current, None, "skip", [f"current OK: {why}"])
        evidence.append(f"current {current} -> {why}")

        # Strategy 1: ATS posting JSON
        ats = company.get("ats", {})
        candidates = await gather_ats_candidates(client, ats)

        # Strategy 2: TLD/prefix variants
        for cand in candidate_tld_variants(slug):
            candidates.append((cand, "tld-variant"))

        providers = list(ats.keys())
        proposal = await evaluate_candidates(
            client, candidates, slug, name, current, providers, evidence
        )

        if proposal is not None:
            return proposal
        return Proposal(slug, name, current, None, "none", evidence)


def apply_proposals(to_apply: dict[str, str], file_path: Path) -> int:
    """Rewrite the YAML file in place to update domains."""
    text = file_path.read_text()
    new_lines: list[str] = []
    current_slug: str | None = None
    changes = 0
    for line in text.splitlines(keepends=True):
        m = SLUG_RE.match(line)
        if m:
            current_slug = m.group(1)
        elif current_slug in to_apply and DOMAIN_RE.match(line):
            indent = INDENT_RE.match(line).group(1)
            new_line = f"{indent}domain: {to_apply[current_slug]}\n"
            if new_line != line:
                new_lines.append(new_line)
                changes += 1
                current_slug = None
                continue
        new_lines.append(line)
    file_path.write_text("".join(new_lines))
    return changes


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Rewrite the YAML in place for high-confidence proposals.")
    parser.add_argument("--include-medium", action="store_true", help="Also apply medium-confidence proposals (review the diff carefully).")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--only", nargs="*", help="Restrict to these slugs.")
    args = parser.parse_args()

    companies = yaml.safe_load(DATA_PATH.read_text())
    if args.only:
        wanted = set(args.only)
        companies = [c for c in companies if c["slug"] in wanted]

    sem = asyncio.Semaphore(args.concurrency)
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers, http2=False) as client:
        proposals = await asyncio.gather(*(repair_one(client, c, sem) for c in companies))

    by_conf: dict[str, list[Proposal]] = {"high": [], "medium": [], "none": [], "skip": []}
    for p in proposals:
        by_conf[p.confidence].append(p)

    report = {
        "summary": {k: len(v) for k, v in by_conf.items()},
        "proposals": [
            {
                "slug": p.slug,
                "name": p.name,
                "current_domain": p.current_domain,
                "proposed_domain": p.new_domain,
                "confidence": p.confidence,
                "evidence": p.evidence,
            }
            for p in proposals
            if p.confidence != "skip"
        ],
    }
    print(json.dumps(report, indent=2))

    if not args.apply:
        return 0

    accept = {"high"}
    if args.include_medium:
        accept.add("medium")
    to_apply = {p.slug: p.new_domain for p in proposals if p.confidence in accept and p.new_domain}
    if not to_apply:
        print("No proposals to apply.", file=sys.stderr)
        return 0

    changes = apply_proposals(to_apply, DATA_PATH)
    print(f"Applied {changes} domain updates.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
