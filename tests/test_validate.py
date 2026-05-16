import unittest
import sys
from pathlib import Path

# Add scripts directory to path to import validate
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from validate import assert_valid_urls

class TestAssertValidUrls(unittest.TestCase):

    def test_valid_http_https(self):
        companies = [
            {
                "name": "Acme",
                "careers_url": "https://example.com/careers",
                "sources": ["http://example.com"]
            }
        ]
        # Should not raise any exception
        assert_valid_urls(companies)

    def test_invalid_scheme(self):
        companies = [
            {
                "name": "Acme",
                "careers_url": "ftp://example.com/careers",
                "sources": []
            }
        ]
        with self.assertRaises(ValueError) as context:
            assert_valid_urls(companies)
        self.assertIn("Acme has invalid URL: ftp://example.com/careers", str(context.exception))

    def test_missing_scheme(self):
        companies = [
            {
                "name": "Acme",
                "careers_url": "example.com/careers",
                "sources": []
            }
        ]
        with self.assertRaises(ValueError) as context:
            assert_valid_urls(companies)
        self.assertIn("Acme has invalid URL: example.com/careers", str(context.exception))

    def test_missing_netloc(self):
        companies = [
            {
                "name": "Acme",
                "careers_url": "https:///path",
                "sources": []
            }
        ]
        with self.assertRaises(ValueError) as context:
            assert_valid_urls(companies)
        self.assertIn("Acme has invalid URL: https:///path", str(context.exception))

        companies_2 = [
            {
                "name": "Acme",
                "careers_url": "https://",
                "sources": []
            }
        ]
        with self.assertRaises(ValueError) as context:
            assert_valid_urls(companies_2)
        self.assertIn("Acme has invalid URL: https://", str(context.exception))

    def test_invalid_in_sources(self):
        companies = [
            {
                "name": "Acme",
                "careers_url": "https://example.com/careers",
                "sources": ["https://valid.com", "ftp://invalid.com"]
            }
        ]
        with self.assertRaises(ValueError) as context:
            assert_valid_urls(companies)
        self.assertIn("Acme has invalid URL: ftp://invalid.com", str(context.exception))

    def test_multiple_companies(self):
        companies = [
            {
                "name": "Valid Corp",
                "careers_url": "https://valid.com",
                "sources": []
            },
            {
                "name": "Invalid Corp",
                "careers_url": "https://invalid.com",
                "sources": ["http://"]
            }
        ]
        with self.assertRaises(ValueError) as context:
            assert_valid_urls(companies)
        self.assertIn("Invalid Corp has invalid URL: http://", str(context.exception))

if __name__ == '__main__':
    unittest.main()
