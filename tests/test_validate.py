import unittest
import sys
from pathlib import Path

# Add scripts directory to path to import validate
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from validate import assert_valid_urls
import pytest
import validate
from scripts.validate import normalize


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
import tempfile

from scripts.validate import load_yaml

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


def test_normalize():
    # Basic cases
    assert validate.normalize("Hello World") == "hello-world"
    assert validate.normalize("123 Test") == "123-test"

    # Cases with multiple non-alphanumeric chars
    assert validate.normalize("Hello!!! World") == "hello-world"
    assert validate.normalize("  spaced out  ") == "spaced-out"

    # Cases with trailing/leading dashes getting stripped
    assert validate.normalize("-hello-world-") == "hello-world"
    assert validate.normalize("!!!test!!!") == "test"

    # Empty string and edge cases
    assert validate.normalize("") == ""
    assert validate.normalize("!") == ""

def test_load_yaml_valid_list(tmp_path):
    # Create a dummy yaml file with a list
    test_file = tmp_path / "test.yml"
    test_file.write_text("- name: test\n  value: 123", encoding="utf-8")

    data = validate.load_yaml(test_file)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0] == {"name": "test", "value": 123}

def test_load_yaml_invalid_type(tmp_path):
    # Create a dummy yaml file with a dict instead of list
    test_file = tmp_path / "test.yml"
    test_file.write_text("name: test\nvalue: 123", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a top-level list"):
        validate.load_yaml(test_file)

def test_load_yaml_empty_file(tmp_path):
    # Create an empty yaml file
    test_file = tmp_path / "test.yml"
    test_file.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a top-level list"):
        validate.load_yaml(test_file)


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
import tempfile

from scripts.validate import load_yaml

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


def test_normalize_standard_strings():
    assert normalize("Hello World") == "hello-world"
    assert normalize("Acme Inc.") == "acme-inc"
    assert normalize("1Password") == "1password"

def test_normalize_consecutive_special_characters():
    assert normalize("  Foo   Bar  ") == "foo-bar"

def test_normalize_empty_string():
    assert normalize("") == ""

def test_normalize_only_special_characters():
    assert normalize(" !@#$% ") == ""

def test_normalize_leading_trailing_special_characters():
    assert normalize("-hello-") == "hello"
    assert normalize("__hello__") == "hello"

def test_normalize_unicode():
    assert normalize("Café") == "caf"

def test_normalize_domain_specific_punctuation():
    assert normalize("C++") == "c"
    assert normalize(".NET") == "net"
    assert normalize("O'Reilly") == "o-reilly"
    assert normalize("H&R Block") == "h-r-block"

if __name__ == "__main__":
    import unittest
    unittest.main()
