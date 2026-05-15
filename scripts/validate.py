#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "companies.yml"
SCHEMA_PATH = ROOT / "schemas" / "company.schema.json"
README_PATH = ROOT / "README.md"
CATEGORIES_DIR = ROOT / "docs" / "categories"


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def load_yaml(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a top-level list")
    return data


def load_schema(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def assert_valid_urls(companies: list[dict]) -> None:
    for company in companies:
        urls = [company["careers_url"], *company["sources"]]
        for url in urls:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"{company['name']} has invalid URL: {url}")


def assert_unique_keys(companies: list[dict]) -> None:
    seen_names: set[str] = set()
    seen_slugs: set[str] = set()
    seen_ats: set[tuple[str, str]] = set()

    for company in companies:
        normalized_name = normalize(company["name"])
        if normalized_name in seen_names:
            raise ValueError(f"Duplicate company name: {company['name']}")
        seen_names.add(normalized_name)

        slug = company["slug"]
        if slug in seen_slugs:
            raise ValueError(f"Duplicate company slug: {slug}")
        seen_slugs.add(slug)

        for provider, value in company["ats"].items():
            values = value if isinstance(value, list) else [value]
            for board_slug in values:
                ats_key = (provider, board_slug)
                if ats_key in seen_ats:
                    raise ValueError(f"Duplicate ATS slug: {provider}:{board_slug}")
                seen_ats.add(ats_key)


def assert_readme_mentions(companies: list[dict]) -> None:
    # The README is a compact index; individual companies live in
    # docs/categories/<slug>.md. Search both so a company can be mentioned
    # in either surface.
    haystacks = [README_PATH.read_text(encoding="utf-8")]
    if CATEGORIES_DIR.is_dir():
        for path in sorted(CATEGORIES_DIR.glob("*.md")):
            haystacks.append(path.read_text(encoding="utf-8"))
    corpus = "\n".join(haystacks)
    missing = [company["name"] for company in companies if company["name"] not in corpus]
    if missing:
        raise ValueError(f"README is missing companies: {', '.join(missing)}")


def assert_readme_count(companies: list[dict]) -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    expected = f"Currently tracking **{len(companies)} companies**."
    if expected not in readme:
        raise ValueError(f"README count is stale; expected: {expected}")


def main() -> int:
    companies = load_yaml(DATA_PATH)
    schema = load_schema(SCHEMA_PATH)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(companies), key=lambda error: error.path)
    if errors:
        for error in errors:
            path = ".".join(str(part) for part in error.absolute_path) or "<root>"
            print(f"{path}: {error.message}", file=sys.stderr)
        return 1

    assert_valid_urls(companies)
    assert_unique_keys(companies)
    assert_readme_mentions(companies)
    assert_readme_count(companies)

    print(f"Validated {len(companies)} companies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
