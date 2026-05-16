import pytest
from scripts.repair_domain import is_noise

def test_is_noise_exact_match():
    assert is_noise("ashbyhq.com") is True
    assert is_noise("linkedin.com") is True
    assert is_noise("github.com") is True

def test_is_noise_with_www_prefix():
    assert is_noise("www.ashbyhq.com") is True
    assert is_noise("www.linkedin.com") is True
    assert is_noise("www.github.com") is True

def test_is_noise_endswith_cloudfront():
    assert is_noise("d1234567.cloudfront.net") is True
    assert is_noise("foo.bar.cloudfront.net") is True
    assert is_noise("www.d1234567.cloudfront.net") is True

def test_is_noise_endswith_amazonaws():
    assert is_noise("s3-us-west-2.amazonaws.com") is True
    assert is_noise("my-bucket.s3.amazonaws.com") is True
    assert is_noise("www.my-bucket.s3.amazonaws.com") is True

def test_is_noise_case_insensitivity():
    assert is_noise("GITHUB.COM") is True
    assert is_noise("Www.Linkedin.Com") is True
    assert is_noise("Foo.CloudFront.Net") is True

def test_is_noise_negative_cases():
    assert is_noise("example.com") is False
    assert is_noise("mycompany.io") is False
    assert is_noise("cloudfront.com") is False
    assert is_noise("amazonaws.org") is False
    assert is_noise("www.mycompany.io") is False
    assert is_noise("github.com.example.com") is False
    assert is_noise("ashbyhq.com.au") is False
