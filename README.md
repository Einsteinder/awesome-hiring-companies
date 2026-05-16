# Awesome Hiring Companies [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

A curated list of technology companies with public job boards, structured ATS slugs, and source links.

Currently tracking **2144 companies**.

This repository is designed for two uses:

- Human readers can discover companies worth tracking.
- Crawlers can consume `data/companies.yml` as a clean seed list.

## Contents

- [Selection Criteria](#selection-criteria)
- [Inclusion Standard](#inclusion-standard)
- [Categories](#categories)
- [Data Format](#data-format)
- [Contributing](#contributing)

## Selection Criteria

A company belongs here when it has:

- A public jobs or careers page.
- A stable company identity, domain, and source URL.
- Hiring relevance for software, data, product, design, operations, or go-to-market roles.
- Enough public signal to be useful to job seekers or recruiting tools.

This is a curated list, not a dump of every company on the internet.

## Inclusion Standard

New companies must pass the full [`Inclusion Standard`](docs/inclusion-standard.md) before being added.

## Categories

Each category lives in its own file under [`docs/categories/`](docs/categories/).

| Category | Companies |
| --- | ---: |
| [AI and Data](docs/categories/ai-and-data.md) | 188 |
| [Developer Infrastructure](docs/categories/developer-infrastructure.md) | 183 |
| [Fintech](docs/categories/fintech.md) | 200 |
| [Consumer and Marketplace](docs/categories/consumer-and-marketplace.md) | 135 |
| [Healthcare and Biotech](docs/categories/healthcare-and-biotech.md) | 133 |
| [Industrials and Climate](docs/categories/industrials-and-climate.md) | 191 |
| [B2B Enterprise](docs/categories/b2b-enterprise.md) | 76 |
| [Open Source and Platform](docs/categories/open-source-and-platform.md) | 1063 |

## Data Format

The machine-readable source is [`data/companies.yml`](data/companies.yml).

Each entry includes:

- `name` - Canonical company name.
- `slug` - Stable normalized identifier.
- `domain` - Primary domain.
- `careers_url` - Public careers or jobs URL.
- `category` - Broad grouping for discovery.
- `ats` - Known ATS board slugs, such as Greenhouse, Lever, or Ashby.
- `tags` - Useful filtering labels.
- `sources` - Public source URLs used to verify the entry.

Validate the data locally:

```sh
python -m pip install -r requirements.txt
python scripts/validate.py
```

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request.
