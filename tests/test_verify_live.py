import pytest
from scripts.verify_live import ats_slug_values

def test_ats_slug_values_string():
    """Test that a single string input is converted to a list of one string."""
    assert ats_slug_values("greenhouse") == ["greenhouse"]

def test_ats_slug_values_list():
    """Test that a list input is returned unchanged."""
    assert ats_slug_values(["greenhouse", "lever"]) == ["greenhouse", "lever"]

def test_ats_slug_values_empty_list():
    """Test that an empty list input is returned unchanged."""
    assert ats_slug_values([]) == []
