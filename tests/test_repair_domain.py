import pytest
import sys
from pathlib import Path

# Add scripts directory to sys.path so we can import repair_domain
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from repair_domain import normalize_host

def test_normalize_host_removes_www():
    assert normalize_host("www.example.com") == "example.com"

def test_normalize_host_lowercases():
    assert normalize_host("Example.com") == "example.com"
    assert normalize_host("WWW.EXAMPLE.COM") == "example.com"

def test_normalize_host_no_www():
    assert normalize_host("example.com") == "example.com"

def test_normalize_host_preserves_inner_www():
    assert normalize_host("awww.com") == "awww.com"
    assert normalize_host("www.awww.com") == "awww.com"
    assert normalize_host("example.www.com") == "example.www.com"

def test_normalize_host_multiple_www():
    assert normalize_host("www.www.example.com") == "www.example.com"
