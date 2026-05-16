# Contributing

This repository is a curated list of companies with public hiring signals. Keep entries useful for job seekers and crawler seed data.

Before adding a company, confirm it passes the [`Inclusion Standard`](docs/inclusion-standard.md).

## Add a Company

Update both files:

- `data/companies.yml` for machine-readable crawler data.
- `README.md` for the human-readable Awesome list.

Each company should include:

- A canonical name and primary domain.
- A public careers or jobs URL.
- At least one source URL.
- At least one ATS slug when known.
- At least one current opening in North America: the United States, Canada,
  Mexico, or a remote role not explicitly limited to another region.
- A short README description explaining why the company is useful to track.

### Workday format

For Ashby, Greenhouse, Lever, Workable, and SmartRecruiters the `ats`
value is the provider's slug. **Workday is an exception**: the value
must be the full host plus site path, separated by a slash:

```yaml
ats:
  workday: nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite
```

A bare slug like `workday: nvidia` is not enough — Workday tenants live
on different pods (`wd1`, `wd5`, `wd12`, …) and use tenant-specific
external-site keys that aren't derivable from the slug. To find the
correct value for a tenant, open the company's careers page in a
browser; the URL is `https://<host>/en-US/<site>/jobs` and the host +
site segment is what goes in the YAML. See
[Inclusion Standard → ATS Value Format](docs/inclusion-standard.md#ats-value-format)
for the worked example. `scripts/verify_live.py` rejects any Workday
entry that's still in bare-slug form.

## Quality Bar

Do not add:

- Companies without public jobs or careers pages.
- Companies without a currently public North America or eligible remote opening.
- Duplicate companies under alternate spellings.
- Dead job boards.
- Private notes, scraped personal data, or non-public information.

Prefer stable source links over third-party commentary.

## Validation

Run this before opening a pull request:

```sh
python -m pip install -r requirements.txt
python scripts/validate.py
python scripts/verify_live.py --only <your-slug> --require-north-america-openings
```

`validate.py` checks the YAML schema, uniqueness, and README mentions.
`verify_live.py` hits the live careers page and ATS endpoint — this is the
authoritative reachability check. The schema does not detect a domain that
parses correctly but doesn't actually resolve. For newly added companies,
`--require-north-america-openings` also checks supported ATS payloads for at
least one current opening in the United States, Canada, Mexico, an explicit
North America remote region, or a remote role not explicitly limited to another
region.

### Optional: install the pre-push hook

The repository ships a pre-push hook at `scripts/pre_push_verify.sh` that
verifies only the entries you've added or modified on the current branch.
Install it once per clone:

```sh
ln -s ../../scripts/pre_push_verify.sh .git/hooks/pre-push
```

Bypass for an emergency push with `SKIP_VERIFY=1 git push`; CI will still
verify on the PR side.

## Workflow

Pull requests only. **Do not push directly to `main`**, even as a repo
maintainer — `main` is the published seed list that crawlers and humans
consume, and a bad careers URL or wrong ATS slug pollutes the data until
the nightly `verify-live` job catches it.

Every PR that touches `data/companies.yml`, `schemas/company.schema.json`,
or `scripts/verify_live.py` runs the `verify-diff` workflow, which verifies
only the entries that changed. It must pass before merge.

Bulk additions (more than ~10 entries in one PR) need extra care:

- Run `verify_live.py --only <slug-list>` locally first, not just
  `validate.py`. The schema happily accepts well-formed but factually
  wrong URLs.
- Prefer adding the company under its real `ats` provider
  (`workday:<tenant>`, `smartrecruiters:<slug>`, `successfactors:<slug>`,
  `workable:<slug>`, etc.) rather than `custom:<slug>` when the ATS is
  identifiable from the careers page source. `custom:` is a fallback,
  not the default.
- Open each rendered careers page in a real browser before pushing. The
  verifier catches most issues but cannot detect a page that returns
  HTTP 200 yet is actually a marketing page with no jobs.

## Pull Request Checklist

- The company passes the Inclusion Standard.
- The company is listed in `README.md` under its category section.
- The company is listed in `data/companies.yml`.
- The ATS slug is verified against a public jobs page.
- At least one active opening is in North America or is remote without an
  explicit non-North-America region restriction.
- `python scripts/validate.py` passes.
- `python scripts/verify_live.py --only <slug> --require-north-america-openings`
  passes for new companies (or any `warn` is documented as a legitimate WAF
  block, with a browser screenshot).
