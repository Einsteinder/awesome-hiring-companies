from scripts.repair_domain import normalize_host, is_noise, candidate_tld_variants

def test_normalize_host():
    assert normalize_host("www.example.com") == "example.com"
    assert normalize_host("Example.Com") == "example.com"
    assert normalize_host("Www.Example.Com") == "example.com"
    assert normalize_host("blog.example.com") == "blog.example.com"
    assert normalize_host("www.www.example.com") == "www.example.com"

def test_is_noise():
    # Test known noise hosts
    assert is_noise("ashbyhq.com") is True
    assert is_noise("jobs.ashbyhq.com") is True
    assert is_noise("google.com") is True
    assert is_noise("linkedin.com") is True
    assert is_noise("twitter.com") is True

    # Test cloudfront and amazonaws
    assert is_noise("something.cloudfront.net") is True
    assert is_noise("another.amazonaws.com") is True

    # Test with caps and www
    assert is_noise("WWW.GOOGLE.COM") is True
    assert is_noise("Www.Ashbyhq.Com") is True

    # Test non-noise
    assert is_noise("stripe.com") is False
    assert is_noise("succinct.xyz") is False

def test_candidate_tld_variants():
    variants = candidate_tld_variants("succinct")

    # Should contain tlds
    assert "succinct.ai" in variants
    assert "succinct.io" in variants
    assert "succinct.co" in variants

    # Should contain prefixes
    assert "getsuccinct.com" in variants
    assert "gosuccinct.com" in variants
    assert "trysuccinct.com" in variants

    # Should contain suffixes
    assert "succinctapp.com" in variants
    assert "succincthq.com" in variants

    # Check deduplication / no hyphens
    assert "succinct.ai" == variants[0] # assuming order is preserved
    assert len(variants) == len(set(variants))

    # Test hyphenated slug
    variants_dash = candidate_tld_variants("hello-world")

    # Check basic bare cases (without dash)
    assert "helloworld.ai" in variants_dash
    assert "gethelloworld.com" in variants_dash
    assert "helloworldapp.com" in variants_dash

    # Check cases with dash
    assert "hello-world.ai" in variants_dash
    assert "hello-world.io" in variants_dash
