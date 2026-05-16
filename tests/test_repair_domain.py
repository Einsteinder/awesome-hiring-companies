import sys
from pathlib import Path

# Add project root to sys.path to import scripts
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.repair_domain import host_is_self, normalize_host

def test_normalize_host():
    """Test normalization of hostnames."""
    assert normalize_host("www.example.com") == "example.com"
    assert normalize_host("WWW.EXAMPLE.COM") == "example.com"
    assert normalize_host("example.com") == "example.com"
    assert normalize_host("EXAMPLE.COM") == "example.com"
    assert normalize_host("sub.example.com") == "sub.example.com"
    assert normalize_host("www.sub.example.com") == "sub.example.com"

def test_host_is_self_exact_match():
    """Test exact string matches."""
    assert host_is_self("example.com", "example.com") is True
    assert host_is_self("sub.example.com", "sub.example.com") is True

def test_host_is_self_case_insensitive():
    """Test case insensitivity."""
    assert host_is_self("ExAmPlE.com", "example.COM") is True
    assert host_is_self("Sub.Example.Com", "sub.example.com") is True

def test_host_is_self_www_removal():
    """Test ignoring of 'www.' prefix."""
    assert host_is_self("www.example.com", "example.com") is True
    assert host_is_self("example.com", "www.example.com") is True
    assert host_is_self("www.example.com", "www.example.com") is True

def test_host_is_self_subdomain():
    """Test final host being a subdomain of candidate."""
    assert host_is_self("example.com", "app.example.com") is True
    assert host_is_self("example.com", "a.b.c.example.com") is True

def test_host_is_self_not_subdomain_but_substring():
    """Test final host merely ending with candidate string but without dot."""
    assert host_is_self("example.com", "notexample.com") is False
    assert host_is_self("example.com", "myexample.com") is False

def test_host_is_self_different_domain():
    """Test completely different domains."""
    assert host_is_self("example.com", "other.com") is False
    assert host_is_self("example.com", "example.org") is False

def test_host_is_self_candidate_is_subdomain():
    """Test when candidate is a subdomain and final host is the apex."""
    # If candidate is a subdomain, and final host is the apex, this should be False
    # because they redirected to a broader site, potentially losing specificity
    assert host_is_self("app.example.com", "example.com") is False

def test_host_is_self_both_subdomains():
    """Test when both are different subdomains."""
    assert host_is_self("app.example.com", "api.example.com") is False
