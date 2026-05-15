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
- A short README description explaining why the company is useful to track.

## Quality Bar

Do not add:

- Companies without public jobs or careers pages.
- Duplicate companies under alternate spellings.
- Dead job boards.
- Private notes, scraped personal data, or non-public information.

Prefer stable source links over third-party commentary.

## Validation

Run this before opening a pull request:

```sh
python -m pip install -r requirements.txt
python scripts/validate.py
```

## Pull Request Checklist

- The company passes the Inclusion Standard.
- The company is listed in `README.md`.
- The company is listed in `data/companies.yml`.
- The ATS slug is verified against a public jobs page.
- `python scripts/validate.py` passes.
