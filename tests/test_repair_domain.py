import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.repair_domain import normalize_host, is_noise, candidate_tld_variants

class TestRepairDomain(unittest.TestCase):
    def test_normalize_host(self):
        self.assertEqual(normalize_host("www.example.com"), "example.com")
        self.assertEqual(normalize_host("Example.Com"), "example.com")
        self.assertEqual(normalize_host("Www.Example.Com"), "example.com")
        self.assertEqual(normalize_host("blog.example.com"), "blog.example.com")
        self.assertEqual(normalize_host("www.www.example.com"), "www.example.com")

    def test_is_noise(self):
        # Test known noise hosts
        self.assertTrue(is_noise("ashbyhq.com"))
        self.assertTrue(is_noise("jobs.ashbyhq.com"))
        self.assertTrue(is_noise("google.com"))
        self.assertTrue(is_noise("linkedin.com"))
        self.assertTrue(is_noise("twitter.com"))

        # Test cloudfront and amazonaws
        self.assertTrue(is_noise("something.cloudfront.net"))
        self.assertTrue(is_noise("another.amazonaws.com"))

        # Test with caps and www
        self.assertTrue(is_noise("WWW.GOOGLE.COM"))
        self.assertTrue(is_noise("Www.Ashbyhq.Com"))

        # Test non-noise
        self.assertFalse(is_noise("stripe.com"))
        self.assertFalse(is_noise("succinct.xyz"))

    def test_candidate_tld_variants(self):
        variants = candidate_tld_variants("succinct")

        # Should contain tlds
        self.assertIn("succinct.ai", variants)
        self.assertIn("succinct.io", variants)
        self.assertIn("succinct.co", variants)

        # Should contain prefixes
        self.assertIn("getsuccinct.com", variants)
        self.assertIn("gosuccinct.com", variants)
        self.assertIn("trysuccinct.com", variants)

        # Should contain suffixes
        self.assertIn("succinctapp.com", variants)
        self.assertIn("succincthq.com", variants)

        # Check deduplication / no hyphens
        self.assertEqual(variants[0], "succinct.ai") # assuming order is preserved
        self.assertEqual(len(variants), len(set(variants)))

        # Test hyphenated slug
        variants_dash = candidate_tld_variants("hello-world")

        # Check basic bare cases (without dash)
        self.assertIn("helloworld.ai", variants_dash)
        self.assertIn("gethelloworld.com", variants_dash)
        self.assertIn("helloworldapp.com", variants_dash)

        # Check cases with dash
        self.assertIn("hello-world.ai", variants_dash)
        self.assertIn("hello-world.io", variants_dash)

if __name__ == "__main__":
    unittest.main()
