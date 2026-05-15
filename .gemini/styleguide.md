# Review Style Guide

This repo is a curated list of hiring companies. The source of truth is
`data/companies.yml`; `README.md` and `docs/categories/*.md` mirror it for
humans.

## What to flag in PRs

- **Schema drift** — entries in `data/companies.yml` missing any of
  `name`, `slug`, `domain`, `careers_url`, `category`, `ats`, `tags`,
  `sources`.
- **Workday bare-slug** — any `workday:` value that is not in
  `<host>/<site>` form (e.g. `workday: nvidia` is wrong;
  `workday: nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite` is right).
- **`custom:` overuse** — flag when the ATS is identifiable from the
  careers page source (Greenhouse, Lever, Ashby, Workable, SmartRecruiters,
  SuccessFactors) but the entry uses `custom:<slug>`.
- **Inconsistent updates** — a change to `data/companies.yml` that does not
  also update `README.md` and the matching `docs/categories/*.md`, or vice
  versa.
- **Duplicates** — the same company under a different spelling or slug.
- **Bulk additions** — more than ~10 new entries in a single PR. Suggest
  splitting, and remind the author to run
  `scripts/verify_live.py --only <slugs>` locally.

## What NOT to flag

- README per-category counts when the diff is small. The maintainer
  updates these in batches.
- Style of company descriptions in `README.md` — voice is intentionally
  varied.
- Existing entries the PR didn't touch.

## Tone

Terse. Cite the file and line. No emojis. Skip preamble like
"Great PR!" — go straight to findings.
