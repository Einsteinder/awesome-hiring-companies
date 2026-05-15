# Agent Instructions

This file is read by coding agents (Jules, OpenHands, Codex, and others that
honor the `AGENTS.md` convention) when they work on this repository.

Both Jules and OpenHands are wired up. Issues are routed automatically:

- Issues labeled `jules` → handled by Jules (https://jules.google).
- Issues labeled openhands + @openhands mention -> handled by OpenHands (https://app.all-hands.dev).

**One issue, one agent.** A label-exclusivity workflow
(`enforce-agent-labels.yml`) auto-removes a duplicate agent label if both
end up on the same issue. If you somehow see both `jules` and `openhands` on
an issue, **do not act on it** — the workflow will resolve the conflict
within seconds.

**Don't redo work that's already in flight.** Before starting, check if
there's an open PR with `Closes #<this-issue>` or a branch named after
the slug (`fix-<slug>` or `add-<slug>`). If so, the other agent or a
human is already on it; stop and post a comment.

As a safety net, `dedup-pull-requests.yml` auto-closes any new PR that
references the same `Closes #N` as an older open PR. The lower-numbered
PR wins. If your PR gets auto-closed for this reason and the older one
is broken, the comment will tell you how to take over deliberately.

**Always rebase before pushing.** Because `data/companies.yml` is a single
shared file, two concurrent fix-PRs editing different slugs can still
collide on adjacent lines or on README per-category counts. Run
`git pull --rebase origin main` and resolve any conflict before pushing.

This repository is a curated Awesome list of hiring companies. The
machine-readable source of truth is `data/companies.yml`; `README.md` and the
files under `docs/categories/` are the human-readable mirror.

## Typical issues you will be asked to address

1. **Add a company** — usually a name and a careers URL.
2. **Fix a broken or moved careers URL.**
3. **Correct an ATS slug** (Greenhouse, Lever, Ashby, Workday, etc.).
4. **Remove a dead listing.**

## How to add or modify a company

Touch all three places together — they must stay consistent:

- `data/companies.yml` — add the entry, alphabetized within its category.
- `README.md` — update the per-category company count if you changed totals.
- `docs/categories/<category>.md` — add or update the company line.

Every entry needs: `name`, `slug`, `domain`, `careers_url`, `category`, `ats`,
`tags`, `sources`. See existing entries for the exact shape, and the
**Field format rules** below for what each one must look like.

### Field format rules

The schema (`schemas/company.schema.json`) enforces specific patterns.
Common failures from agent-generated PRs come from getting these wrong:

- **`slug`** — lowercase kebab-case ASCII. Pattern:
  `^[a-z0-9]+(?:-[a-z0-9]+)*$`. Derive from `name` by lowercasing and
  collapsing any non-alphanumeric run into a single `-`. Examples:
  `OpenAI` → `openai`, `Acme Inc.` → `acme-inc`, `1Password` → `1password`.
- **`domain`** — lowercase bare domain only. No `https://`, no path, no
  trailing slash. Pattern: `^[a-z0-9][a-z0-9.-]+\.[a-z]{2,}$`.
  Examples: `anthropic.com`, `nvidia.com`. Wrong: `https://anthropic.com/`.
- **`category`** — kebab-case enum from the schema, **not** the display
  label shown in `README.md`. Convert by lowercasing the display label
  and replacing spaces with `-`:
    - `AI and Data` → `ai-and-data`
    - `Developer Infrastructure` → `developer-infrastructure`
    - `Fintech` → `fintech`
    - `Consumer and Marketplace` → `consumer-and-marketplace`
    - `Healthcare and Biotech` → `healthcare-and-biotech`
    - `Industrials and Climate` → `industrials-and-climate`
    - `B2B Enterprise` → `b2b-enterprise`
    - `Open Source and Platform` → `open-source-and-platform`
- **`tags`** — lowercase kebab-case, same pattern as `slug`. At least one.
- **`ats`** — object with at least one provider key. Standard providers:
    - `greenhouse:<slug>`, `lever:<slug>`, `ashby:<slug>`,
      `workable:<slug>`, `smartrecruiters:<slug>`, `successfactors:<slug>`
    - `workday:<host>/<site>` — see the Workday section below
    - `custom:<slug>` — **fallback only** when no real ATS is identifiable
      from the careers page source. Prefer the real provider whenever
      possible; `custom` will pass schema validation but is discouraged.
- **`sources`** — at least one full URL with scheme. `careers_url` is
  separate and also required.

### Workday is special

For Workday the `ats` value is **not** a bare slug. It must be the full host
plus site path:

```yaml
ats:
  workday: nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite
```

`verify_live.py` rejects bare-slug Workday entries. See
`docs/inclusion-standard.md` for the full rule.

## Validation — run before opening a PR

```sh
python -m pip install -r requirements.txt
python scripts/validate.py
python scripts/verify_live.py --only <slug-you-added-or-changed>
```

Both must pass. `validate.py` checks schema, uniqueness, and README mentions.
`verify_live.py` hits the live careers page and ATS endpoint — this is the
authoritative reachability check, not optional.

If `verify_live.py` returns a `warn` for a legitimate WAF block (Cloudflare,
PerimeterX), note it in the PR body with a browser screenshot. Do not
suppress the warning silently.

## PR conventions

- One company per PR for adds; grouped fixes are fine for URL/ATS corrections.
- Branch name: `add-<slug>` or `fix-<slug>`.
- PR title: short, imperative — e.g. `Add Anthropic`, `Fix Stripe careers URL`.
- Reference the originating issue with `Closes #N`.
- Do not push directly to `main`. Pull requests only.

## Quality bar — do not merge entries that

- Lack a public careers or jobs page.
- Duplicate an existing company under a different spelling.
- Point at a dead job board or a marketing page with no jobs.
- Use `custom:<slug>` when the real ATS is identifiable from the page source.

## Out of scope for the agent

- Bulk additions of more than ~10 companies in a single PR. Flag the issue
  for human review instead — the live-verify step needs careful manual
  inspection at that volume.
- Changes to `schemas/company.schema.json` or `scripts/verify_live.py`
  beyond minor fixes. Tag the maintainer.
- Removing companies because of subjective signals (layoffs, news). Only
  remove if the careers page is genuinely dead.
