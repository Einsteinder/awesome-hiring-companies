import pytest
from validate import assert_unique_keys

def test_assert_unique_keys_empty():
    assert_unique_keys([])

def test_assert_unique_keys_valid():
    companies = [
        {"name": "Company A", "slug": "company-a", "ats": {"greenhouse": "companya"}},
        {"name": "Company B", "slug": "company-b", "ats": {"lever": "companyb"}},
    ]
    assert_unique_keys(companies)

def test_assert_unique_keys_duplicate_name():
    companies = [
        {"name": "Company A", "slug": "company-a", "ats": {"greenhouse": "companya"}},
        {"name": "Company A", "slug": "company-a-2", "ats": {"lever": "companyb"}},
    ]
    with pytest.raises(ValueError, match="Duplicate company name: Company A"):
        assert_unique_keys(companies)

def test_assert_unique_keys_duplicate_name_normalized():
    companies = [
        {"name": "Company A!", "slug": "company-a", "ats": {"greenhouse": "companya"}},
        {"name": "Company a", "slug": "company-a-2", "ats": {"lever": "companyb"}},
    ]
    with pytest.raises(ValueError, match="Duplicate company name: Company a"):
        assert_unique_keys(companies)

def test_assert_unique_keys_duplicate_slug():
    companies = [
        {"name": "Company A", "slug": "company", "ats": {"greenhouse": "companya"}},
        {"name": "Company B", "slug": "company", "ats": {"lever": "companyb"}},
    ]
    with pytest.raises(ValueError, match="Duplicate company slug: company"):
        assert_unique_keys(companies)

def test_assert_unique_keys_duplicate_ats():
    companies = [
        {"name": "Company A", "slug": "company-a", "ats": {"greenhouse": "companya"}},
        {"name": "Company B", "slug": "company-b", "ats": {"greenhouse": "companya"}},
    ]
    with pytest.raises(ValueError, match="Duplicate ATS slug: greenhouse:companya"):
        assert_unique_keys(companies)

def test_assert_unique_keys_same_ats_slug_different_provider():
    companies = [
        {"name": "Company A", "slug": "company-a", "ats": {"greenhouse": "companya"}},
        {"name": "Company B", "slug": "company-b", "ats": {"lever": "companya"}},
    ]
    assert_unique_keys(companies)

def test_assert_unique_keys_ats_list():
    companies = [
        {"name": "Company A", "slug": "company-a", "ats": {"greenhouse": ["companya1", "companya2"]}},
        {"name": "Company B", "slug": "company-b", "ats": {"lever": "companyb"}},
    ]
    assert_unique_keys(companies)

def test_assert_unique_keys_duplicate_ats_in_list():
    companies = [
        {"name": "Company A", "slug": "company-a", "ats": {"greenhouse": ["companya1", "companya2"]}},
        {"name": "Company B", "slug": "company-b", "ats": {"greenhouse": "companya2"}},
    ]
    with pytest.raises(ValueError, match="Duplicate ATS slug: greenhouse:companya2"):
        assert_unique_keys(companies)

def test_assert_unique_keys_duplicate_ats_within_same_company():
    companies = [
        {"name": "Company A", "slug": "company-a", "ats": {"greenhouse": ["companya", "companya"]}},
    ]
    with pytest.raises(ValueError, match="Duplicate ATS slug: greenhouse:companya"):
        assert_unique_keys(companies)
