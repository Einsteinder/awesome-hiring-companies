# Inclusion Standard

This list accepts companies that are useful as verified hiring-discovery seeds.

Add a company only when it passes every required criterion and none of the exclusion criteria. Preferred signals help prioritize additions, but they are not mandatory.

## Required Criteria

- The company has an official public careers page, jobs page, or ATS job board.
- The company has a stable identity: canonical name, primary domain, and no obvious duplicate entry.
- The careers URL is reachable without login, private access, or a one-off referral link.
- The entry has at least one official source URL, preferably the careers page itself.
- The company is relevant to software, data, AI, product, design, operations, finance, recruiting, sales, marketing, or other technology-adjacent roles.
- The entry includes a crawlable hiring signal, such as an ATS slug or a stable careers URL.
- New entries must have at least one currently public opening in North America
  (the United States, Canada, or Mexico) or a remote opening that is not
  explicitly limited to another region.
- The YAML entry follows the schema in `schemas/company.schema.json`.
- The README entry explains why the company is useful to track.

## Preferred Signals

- The company has active openings or has shown recent public hiring activity.
- The company has multiple active North America openings, remote openings, or
  an explicit North America remote hiring region.
- The company uses a supported ATS such as Ashby, Greenhouse, or Lever.
- The company has strong engineering, product, data, AI, platform, or go-to-market hiring relevance.
- The company has clear public identity signals, such as a well-known domain, public funding, public market status, notable product, or open-source footprint.
- The company has enough stable metadata to support crawler enrichment later, such as location, stage, sector, or known job-board provider.

## Exclusion Criteria

Do not add:

- Job boards, scraping sites, staffing agencies, or recruiting agencies unless the list explicitly adds a separate category for them later.
- Companies with no official careers or jobs page.
- Companies with no currently public North America or eligible remote openings.
- Companies whose only evidence is a third-party job post.
- Dead, login-only, invite-only, or captcha-only job boards.
- Duplicate companies under alternate spellings, subsidiaries, aliases, or old names unless the hiring brand is clearly separate.
- Private notes, personal data, leaked information, or non-public sources.
- Scam-like, deceptive, illegal, unpaid-only, or multi-level-marketing opportunities.

## Data Standard

Every company in `data/companies.yml` must include:

```yaml
- name: Example
  slug: example
  domain: example.com
  careers_url: https://jobs.ashbyhq.com/example
  category: developer-infrastructure
  ats:
    ashby: example
  tags:
    - developer-tools
  sources:
    - https://jobs.ashbyhq.com/example
```

Field rules:

- `name` is the public company name.
- `slug` is a stable lowercase kebab-case identifier.
- `domain` is the primary company domain, without `https://`.
- `careers_url` is the best official URL for discovering open roles.
- `category` must use one of the categories allowed by the schema.
- `ats` should contain verified provider slugs when known.
- `tags` must be lowercase kebab-case and should describe sector, product area, role relevance, or platform.
- `sources` should prefer official company URLs over third-party pages.

### ATS Value Format

For most providers the `ats` value is the provider's slug:

```yaml
ats:
  ashby: openai          # https://jobs.ashbyhq.com/openai
  greenhouse: databricks # https://boards-api.greenhouse.io/v1/boards/databricks/jobs
  lever: spotify         # https://api.lever.co/v0/postings/spotify
  workable: huggingface  # https://apply.workable.com/huggingface
  smartrecruiters: SAP   # https://api.smartrecruiters.com/v1/companies/SAP/postings
```

**Workday is the one exception**. Its value must be the full host plus
site path, not a bare slug:

```yaml
ats:
  workday: nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite
```

Workday tenants are split across regional pods (`wd1`, `wd5`, `wd12`,
…) and each tenant uses its own external-site key (`External`,
`NVIDIAExternalCareerSite`, `disneycareer`, …) that can't be derived
from the slug alone. Crawlers need the full host + site to call the
cxs API. To find the values for a new tenant, open the company's
careers page; the URL encodes the pod and site, e.g.
`https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/jobs`
→ `nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite`.

`scripts/verify_live.py` rejects any Workday entry that is still in
bare-slug form.

## Category Standard

Use the narrowest current category that fits:

- `ai-and-data` - AI, machine learning, analytics, databases, and data infrastructure.
- `developer-infrastructure` - Developer tools, cloud, infrastructure, security, observability, and B2B technical platforms.
- `fintech` - Payments, banking, investing, crypto, expense, payroll, or financial infrastructure.
- `consumer-and-marketplace` - Consumer products, communities, marketplaces, media, travel, commerce, education, and gaming.
- `healthcare-and-biotech` - Healthcare delivery, health-tech, biotech, drug discovery, medical devices, and wellness.
- `industrials-and-climate` - Hardware, manufacturing, robotics, climate, energy, aviation, space, supply chain, logistics, real estate, and construction.
- `b2b-enterprise` - B2B SaaS that does not fit `developer-infrastructure`: HR, sales, marketing, operations, recruiting, legal, and procurement.
- `open-source-and-platform` - Open-source companies, broad platforms, productivity, collaboration, and entries that do not fit any other category.

If no category fits, do not force the entry. Open an issue proposing the new category.

## Review Checklist

Before merging a company:

- Open `careers_url` and confirm it is official.
- Verify every ATS slug against the public job board.
- Confirm at least one listed opening is in the United States, Canada, Mexico,
  an explicit North America remote region, or a remote role not limited to
  another region.
- Search `data/companies.yml` for duplicate name, domain, slug, and ATS slug.
- Add a useful README description, not only a link.
- Run `python scripts/validate.py`.
- For new entries, run `python scripts/verify_live.py --only <slug> --require-north-america-openings`.
