import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.verify_live import ats_slug_values

class TestVerifyLive(unittest.TestCase):
    def test_ats_slug_values_string(self):
        """Test that a single string input is converted to a list of one string."""
        self.assertEqual(ats_slug_values("greenhouse"), ["greenhouse"])

    def test_ats_slug_values_list(self):
        """Test that a list input is returned unchanged."""
        self.assertEqual(ats_slug_values(["greenhouse", "lever"]), ["greenhouse", "lever"])

    def test_ats_slug_values_empty_list(self):
        """Test that an empty list input is returned unchanged."""
        self.assertEqual(ats_slug_values([]), [])

if __name__ == "__main__":
    unittest.main()
