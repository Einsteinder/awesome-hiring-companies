import argparse
import subprocess
import sys
import unittest
from unittest.mock import patch, mock_open

# Adjust path so we can import from scripts
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from scripts.diff_slugs import entries_by_slug, load_from_ref, main, DATA_PATH

class TestDiffSlugs(unittest.TestCase):
    def test_entries_by_slug(self):
        entries = [
            {"slug": "apple", "name": "Apple"},
            {"slug": "banana", "name": "Banana"},
            {"name": "No Slug Company"} # Should be ignored
        ]
        expected = {
            "apple": {"slug": "apple", "name": "Apple"},
            "banana": {"slug": "banana", "name": "Banana"}
        }
        self.assertEqual(entries_by_slug(entries), expected)

    def test_entries_by_slug_empty(self):
        self.assertEqual(entries_by_slug([]), {})

    @patch("builtins.open", new_callable=mock_open, read_data="- slug: apple\n  name: Apple\n")
    def test_load_from_ref_none(self, mock_file):
        result = load_from_ref(None)
        mock_file.assert_called_once_with(DATA_PATH, "r", encoding="utf-8")
        self.assertEqual(result, [{"slug": "apple", "name": "Apple"}])

    @patch("builtins.open", new_callable=mock_open, read_data="")
    def test_load_from_ref_none_empty(self, mock_file):
        result = load_from_ref(None)
        self.assertEqual(result, [])

    @patch("subprocess.check_output")
    def test_load_from_ref_with_ref(self, mock_check_output):
        mock_check_output.return_value = b"- slug: banana\n  name: Banana\n"
        result = load_from_ref("origin/main")
        mock_check_output.assert_called_once_with(
            ["git", "show", f"origin/main:{DATA_PATH}"], stderr=subprocess.DEVNULL
        )
        self.assertEqual(result, [{"slug": "banana", "name": "Banana"}])

    @patch("subprocess.check_output")
    def test_load_from_ref_with_ref_empty(self, mock_check_output):
        mock_check_output.return_value = b""
        result = load_from_ref("origin/main")
        self.assertEqual(result, [])

    @patch("subprocess.check_output")
    def test_load_from_ref_with_ref_error(self, mock_check_output):
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "git")
        result = load_from_ref("origin/main")
        self.assertEqual(result, [])

    @patch("sys.argv", ["diff_slugs.py", "--base", "origin/main"])
    @patch("scripts.diff_slugs.load_from_ref")
    def test_main(self, mock_load_from_ref):
        # Setup mock to return different data based on ref
        def load_side_effect(ref):
            if ref == "origin/main":
                return [
                    {"slug": "apple", "name": "Apple"},
                    {"slug": "banana", "name": "Banana"},
                    {"slug": "cherry", "name": "Cherry"}
                ]
            elif ref is None:
                return [
                    {"slug": "apple", "name": "Apple"}, # Unchanged
                    {"slug": "banana", "name": "Banana V2"}, # Changed
                    {"slug": "date", "name": "Date"} # Added
                    # Cherry is removed, but the diff logic only cares about head
                ]
            return []

        mock_load_from_ref.side_effect = load_side_effect

        from io import StringIO
        import contextlib

        f = StringIO()
        with contextlib.redirect_stdout(f):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        # Output should be changed and added slugs from head
        self.assertEqual(f.getvalue(), "banana\ndate\n")

if __name__ == "__main__":
    unittest.main()
