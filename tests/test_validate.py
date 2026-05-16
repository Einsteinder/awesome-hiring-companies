import unittest
import sys
from pathlib import Path

# Add scripts directory to path to import validate
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from validate import assert_valid_urls, load_yaml, normalize
import tempfile

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


class TestValidate(unittest.TestCase):
    def test_load_yaml_valid(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("- name: test\n")
            temp_path = Path(f.name)

        try:
            data = load_yaml(temp_path)
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
        finally:
            temp_path.unlink()

    def test_load_yaml_invalid(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("name: test\n")
            temp_path = Path(f.name)

        try:
            with self.assertRaisesRegex(ValueError, "must contain a top-level list"):
                load_yaml(temp_path)
        finally:
            temp_path.unlink()

    def test_load_yaml_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            with self.assertRaisesRegex(ValueError, "must contain a top-level list"):
                load_yaml(temp_path)
        finally:
            temp_path.unlink()

    def test_normalize(self):
        # Basic cases
        self.assertEqual(normalize("Hello World"), "hello-world")
        self.assertEqual(normalize("123 Test"), "123-test")

        # Cases with multiple non-alphanumeric chars
        self.assertEqual(normalize("Hello!!! World"), "hello-world")
        self.assertEqual(normalize("  spaced out  "), "spaced-out")

        # Cases with trailing/leading dashes getting stripped
        self.assertEqual(normalize("-hello-world-"), "hello-world")
        self.assertEqual(normalize("!!!test!!!"), "test")

        # Empty string and edge cases
        self.assertEqual(normalize(""), "")
        self.assertEqual(normalize("!"), "")


if __name__ == "__main__":
    unittest.main()
