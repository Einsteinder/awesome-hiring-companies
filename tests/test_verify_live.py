import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from verify_live import ats_slug_values


class TestAtsSlugValues(unittest.TestCase):
    def test_string(self):
        self.assertEqual(ats_slug_values("greenhouse"), ["greenhouse"])

    def test_list(self):
        self.assertEqual(ats_slug_values(["greenhouse", "lever"]), ["greenhouse", "lever"])

    def test_empty_list(self):
        self.assertEqual(ats_slug_values([]), [])


if __name__ == "__main__":
    unittest.main()
