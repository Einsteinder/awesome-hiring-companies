# Awesome Hiring Companies [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

A curated list of technology companies with public job boards, structured ATS slugs, and source links.

This repository is designed for two uses:

- Human readers can discover companies worth tracking.
- Crawlers can consume `data/companies.yml` as a clean seed list.

## Contents

- [Selection Criteria](#selection-criteria)
- [AI and Data](#ai-and-data)
- [Developer Infrastructure](#developer-infrastructure)
- [Fintech](#fintech)
- [Consumer and Marketplace](#consumer-and-marketplace)
- [Open Source and Platform](#open-source-and-platform)
- [Data Format](#data-format)
- [Contributing](#contributing)

## Selection Criteria

A company belongs here when it has:

- A public jobs or careers page.
- A stable company identity, domain, and source URL.
- Hiring relevance for software, data, product, design, operations, or go-to-market roles.
- Enough public signal to be useful to job seekers or recruiting tools.

This is a curated list, not a dump of every company on the internet.

## AI and Data

- [OpenAI](https://openai.com) - AI research and product company with roles across research, engineering, infrastructure, policy, and go-to-market.
- [Mistral AI](https://mistral.ai) - AI company building open and commercial frontier models.
- [Databricks](https://databricks.com) - Data and AI platform company with strong infrastructure, database, and ML roles.
- [Browserbase](https://browserbase.com) - Browser automation infrastructure for AI agents and web automation.

## Developer Infrastructure

- [Linear](https://linear.app) - Product development and issue tracking platform known for high-quality engineering and design.
- [PostHog](https://posthog.com) - Open-source product analytics and developer tooling company.
- [Ashby](https://ashbyhq.com) - Recruiting platform and ATS company with engineering-heavy product work.
- [Vercel](https://vercel.com) - Frontend cloud platform for web application deployment and developer workflows.
- [Elastic](https://elastic.co) - Search, observability, and security platform company.

## Fintech

- [Stripe](https://stripe.com) - Payments and financial infrastructure company.
- [Coinbase](https://coinbase.com) - Crypto exchange and blockchain infrastructure company.
- [Ramp](https://ramp.com) - Finance automation platform for corporate cards, expense management, and procurement.
- [Robinhood](https://robinhood.com) - Consumer finance and investing platform.
- [Plaid](https://plaid.com) - Financial data network and banking API platform.

## Consumer and Marketplace

- [Airbnb](https://airbnb.com) - Travel marketplace with large-scale consumer, marketplace, trust, and payments systems.
- [Instacart](https://instacart.com) - Grocery delivery marketplace with logistics, retail, and ads systems.
- [Pinterest](https://pinterest.com) - Visual discovery platform with search, recommendations, ads, and creator products.
- [Reddit](https://reddit.com) - Community platform with consumer, ads, moderation, and infrastructure roles.
- [Discord](https://discord.com) - Communications platform for communities, gaming, and social products.
- [Spotify](https://spotify.com) - Audio streaming platform with consumer, personalization, creator, and ads systems.

## Open Source and Platform

- [GitLab](https://gitlab.com) - DevSecOps platform with a remote-first company model.
- [Cloudflare](https://cloudflare.com) - Edge cloud, security, networking, and developer platform company.
- [Dropbox](https://dropbox.com) - Productivity and storage platform company.
- [Figma](https://figma.com) - Collaborative design and product development platform.
- [Asana](https://asana.com) - Work management platform for teams and organizations.
- [Palantir](https://palantir.com) - Data platform company serving commercial and government customers.
- [Neon](https://neon.tech) - Serverless Postgres platform for developers.

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

