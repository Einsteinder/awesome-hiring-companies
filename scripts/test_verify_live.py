import pytest
from scripts.verify_live import filter_companies

def test_filter_companies_no_slugs():
    companies = [{"slug": "a"}, {"slug": "b"}]
    assert filter_companies(companies, None) == companies
    assert filter_companies(companies, []) == companies

def test_filter_companies_with_slugs():
    companies = [
        {"slug": "a", "name": "A"},
        {"slug": "b", "name": "B"},
        {"slug": "c", "name": "C"}
    ]
    result = filter_companies(companies, ["b", "c"])
    assert len(result) == 2
    assert result[0]["slug"] == "b"
    assert result[1]["slug"] == "c"

def test_filter_companies_missing_slug():
    companies = [{"slug": "a"}, {"name": "b"}]
    result = filter_companies(companies, ["a"])
    assert result == [{"slug": "a"}]

def test_filter_companies_no_match():
    companies = [{"slug": "a"}, {"slug": "b"}]
    result = filter_companies(companies, ["x", "y"])
    assert result == []

def test_filter_companies_duplicate_slugs_in_filter():
    companies = [{"slug": "a"}, {"slug": "b"}]
    result = filter_companies(companies, ["a", "a"])
    assert result == [{"slug": "a"}]

def test_filter_companies_duplicate_companies():
    companies = [{"slug": "a"}, {"slug": "a"}]
    result = filter_companies(companies, ["a"])
    assert result == [{"slug": "a"}, {"slug": "a"}]
