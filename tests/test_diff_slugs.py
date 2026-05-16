import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch, mock_open

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from scripts.diff_slugs import entries_by_slug, load_from_ref, main, DATA_PATH


class TestEntriesBySlug(unittest.TestCase):
    def test_filters_missing_slug(self):
        entries = [
            {"slug": "apple", "name": "Apple"},
            {"slug": "banana", "name": "Banana"},
            {"name": "No Slug Company"},
        ]
        expected = {
            "apple": {"slug": "apple", "name": "Apple"},
            "banana": {"slug": "banana", "name": "Banana"},
        }
        self.assertEqual(entries_by_slug(entries), expected)

    def test_empty(self):
        self.assertEqual(entries_by_slug([]), {})


class TestLoadFromRef(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data="- slug: apple\n  name: Apple\n")
    def test_none_reads_local_file(self, mock_file):
        result = load_from_ref(None)
        mock_file.assert_called_once_with(DATA_PATH, "r", encoding="utf-8")
        self.assertEqual(result, [{"slug": "apple", "name": "Apple"}])

    @patch("builtins.open", new_callable=mock_open, read_data="")
    def test_none_empty(self, mock_file):
        self.assertEqual(load_from_ref(None), [])

    @patch("subprocess.check_output")
    def test_with_ref(self, mock_check_output):
        mock_check_output.return_value = b"- slug: banana\n  name: Banana\n"
        result = load_from_ref("origin/main")
        mock_check_output.assert_called_once_with(
            ["git", "show", f"origin/main:{DATA_PATH}"], stderr=subprocess.DEVNULL
        )
        self.assertEqual(result, [{"slug": "banana", "name": "Banana"}])

    @patch("subprocess.check_output")
    def test_with_ref_empty(self, mock_check_output):
        mock_check_output.return_value = b""
        self.assertEqual(load_from_ref("origin/main"), [])

    @patch("subprocess.check_output")
    def test_with_ref_error_returns_empty(self, mock_check_output):
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "git")
        self.assertEqual(load_from_ref("origin/main"), [])


class TestMain(unittest.TestCase):
    @patch("sys.argv", ["diff_slugs.py", "--base", "origin/main"])
    @patch("scripts.diff_slugs.load_from_ref")
    def test_emits_changed_and_added(self, mock_load_from_ref):
        def load_side_effect(ref):
            if ref == "origin/main":
                return [
                    {"slug": "apple", "name": "Apple"},
                    {"slug": "banana", "name": "Banana"},
                    {"slug": "cherry", "name": "Cherry"},
                ]
            if ref is None:
                return [
                    {"slug": "apple", "name": "Apple"},
                    {"slug": "banana", "name": "Banana V2"},
                    {"slug": "date", "name": "Date"},
                ]
            return []

        mock_load_from_ref.side_effect = load_side_effect

        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(buf.getvalue(), "banana\ndate\n")


if __name__ == "__main__":
    unittest.main()
