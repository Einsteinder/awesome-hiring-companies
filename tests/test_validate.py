import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

import validate
from validate import assert_valid_urls, load_yaml, normalize


class TestAssertValidUrls(unittest.TestCase):

    def test_valid_http_https(self):
        companies = [
            {
                "name": "Acme",
                "careers_url": "https://example.com/careers",
                "sources": ["http://example.com"]
            }
        ]
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


class TestLoadYaml(unittest.TestCase):
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

    def test_load_yaml_invalid_type(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("name: test\nvalue: 123\n")
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


class TestNormalize(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(normalize("Hello World"), "hello-world")
        self.assertEqual(normalize("123 Test"), "123-test")

    def test_multiple_non_alnum(self):
        self.assertEqual(normalize("Hello!!! World"), "hello-world")
        self.assertEqual(normalize("  spaced out  "), "spaced-out")

    def test_strips_dashes(self):
        self.assertEqual(normalize("-hello-world-"), "hello-world")
        self.assertEqual(normalize("!!!test!!!"), "test")

    def test_empty(self):
        self.assertEqual(normalize(""), "")
        self.assertEqual(normalize("!"), "")


if __name__ == "__main__":
    unittest.main()
