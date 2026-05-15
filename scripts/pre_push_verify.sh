#!/usr/bin/env bash
# Pre-push hook: verify any companies.yml entries added or modified on this
# branch against the live ATS endpoints and careers pages before letting the
# push go through.
#
# Install once per checkout:
#   ln -s ../../scripts/pre_push_verify.sh .git/hooks/pre-push
#   chmod +x scripts/pre_push_verify.sh
#
# Honors environment overrides:
#   SKIP_VERIFY=1 git push       # bypass (use sparingly; CI will catch you)
#   BASE_REF=main                # what to diff against (default: origin/main)

set -euo pipefail

if [[ "${SKIP_VERIFY:-0}" == "1" ]]; then
  echo "pre-push: SKIP_VERIFY=1, bypassing live verification"
  exit 0
fi

base="${BASE_REF:-origin/main}"

# Make sure we have the base ref locally.
git fetch origin "${base#origin/}" --depth=1 >/dev/null 2>&1 || true

# Bail early if companies.yml is unchanged.
if git diff --quiet "$base"...HEAD -- data/companies.yml; then
  exit 0
fi

# Collect slugs of added or modified entries.
slugs=$(python3 - <<'PY'
import subprocess, sys
import yaml

def load(ref):
    try:
        blob = subprocess.check_output(
            ["git", "show", f"{ref}:data/companies.yml"],
            text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return {}
    return {c["slug"]: c for c in (yaml.safe_load(blob) or [])
            if isinstance(c, dict) and "slug" in c}

import os
base = load(os.environ.get("BASE_REF", "origin/main"))
head = load("HEAD")
changed = []
for slug, h in head.items():
    if slug not in base:
        changed.append(slug)
        continue
    b = base[slug]
    if (b.get("careers_url") != h.get("careers_url")
        or b.get("ats") != h.get("ats")
        or b.get("sources") != h.get("sources")):
        changed.append(slug)
print(" ".join(sorted(set(changed))))
PY
)

if [[ -z "$slugs" ]]; then
  exit 0
fi

count=$(wc -w <<< "$slugs")
echo "pre-push: verifying $count added or modified entr$([[ $count -eq 1 ]] && echo y || echo ies) live…"

# Run schema + live check, scoped to the diff. --fail-on-warn so a 404 careers
# page is a hard stop (the inclusion standard requires reachability).
python scripts/validate.py
# shellcheck disable=SC2086
python scripts/verify_live.py --only $slugs --fail-on-warn

echo "pre-push: OK"
