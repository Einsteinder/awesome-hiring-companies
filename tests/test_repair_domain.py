import pytest
import sys
import os

# Add the scripts directory to the python path so we can import from it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from repair_domain import is_parked, PARKING_HOSTS

def test_is_parked_known_hosts():
    # Test all hosts in PARKING_HOSTS
    for host in PARKING_HOSTS:
        assert is_parked(host) is True

def test_is_parked_subdomains():
    # Test known hosts with www. subdomain
    for host in PARKING_HOSTS:
        assert is_parked(f"www.{host}") is True

def test_is_parked_uppercase():
    # Test uppercase handling
    for host in PARKING_HOSTS:
        assert is_parked(host.upper()) is True

def test_is_parked_mixed_case():
    # Test mixed case handling
    for host in PARKING_HOSTS:
        mixed_host = "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(host))
        assert is_parked(mixed_host) is True

def test_is_parked_not_parked():
    # Test domains that are not parked
    assert is_parked("google.com") is False
    assert is_parked("example.com") is False
    assert is_parked("ashbyhq.com") is False
    assert is_parked("www.google.com") is False
    assert is_parked("GOOGLE.COM") is False

def test_is_parked_similar_names():
    # Test domains that contain parking host names but are not exact matches
    assert is_parked("not-sedo.com") is False
    assert is_parked("sedo.com.org") is False
    assert is_parked("brandbucket.com.org") is False
    assert is_parked("www.dan.com.co") is False
    assert is_parked("dan.com.mycompany.com") is False
