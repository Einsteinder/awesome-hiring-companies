import pytest
import sys
from pathlib import Path

# Add scripts directory to sys.path so we can import repair_domain
scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from repair_domain import candidate_tld_variants, TLD_VARIANTS, PREFIX_VARIANTS, SUFFIX_VARIANTS

def test_candidate_tld_variants_simple_slug():
    slug = "example"
    candidates = candidate_tld_variants(slug)

    # Verify some variants are generated based on the lists
    if TLD_VARIANTS:
        assert f"{slug}{TLD_VARIANTS[0]}" in candidates
    if PREFIX_VARIANTS:
        assert f"{PREFIX_VARIANTS[0]}{slug}.com" in candidates
    if SUFFIX_VARIANTS:
        assert f"{slug}{SUFFIX_VARIANTS[0]}.com" in candidates

def test_candidate_tld_variants_type():
    slug = "test"
    candidates = candidate_tld_variants(slug)
    assert isinstance(candidates, list)
    if candidates:
        assert isinstance(candidates[0], str)
