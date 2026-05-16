import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from verify_live import (
    Probe,
    Result,
    ats_slug_values,
    find_north_america_job,
    location_mentions_north_america,
    probe_north_america_opening,
    workday_location_facet_jobs,
)


class TestAtsSlugValues(unittest.TestCase):
    def test_string(self):
        self.assertEqual(ats_slug_values("greenhouse"), ["greenhouse"])

    def test_list(self):
        self.assertEqual(ats_slug_values(["greenhouse", "lever"]), ["greenhouse", "lever"])

    def test_empty_list(self):
        self.assertEqual(ats_slug_values([]), [])


class TestNorthAmericaLocationDetection(unittest.TestCase):
    def test_explicit_countries_and_region(self):
        self.assertTrue(location_mentions_north_america("Remote - North America"))
        self.assertTrue(location_mentions_north_america("United States"))
        self.assertTrue(location_mentions_north_america("Canada"))
        self.assertTrue(location_mentions_north_america("Mexico"))

    def test_remote_openings_pass_unless_region_excluded(self):
        self.assertTrue(location_mentions_north_america("Remote"))
        self.assertTrue(location_mentions_north_america("Remote - Worldwide"))
        self.assertFalse(location_mentions_north_america("Remote - EMEA"))
        self.assertFalse(location_mentions_north_america("Remote - APAC"))
        self.assertFalse(location_mentions_north_america("Remote - Latin America"))

    def test_common_city_and_workday_path_locations(self):
        self.assertTrue(location_mentions_north_america("San Francisco, CA"))
        self.assertTrue(location_mentions_north_america("Toronto"))
        self.assertTrue(location_mentions_north_america("/job/US-CA-Santa-Clara/Engineer"))

    def test_non_north_america_locations_do_not_pass(self):
        self.assertFalse(location_mentions_north_america("Paris, France"))
        self.assertFalse(location_mentions_north_america("Latin America"))
        self.assertFalse(location_mentions_north_america("Bogota, DC, Colombia"))
        self.assertFalse(location_mentions_north_america("Can Tho, Vietnam"))

    def test_find_north_america_job_uses_location_fields(self):
        jobs = [
            {"title": "Designer", "location": {"name": "Berlin, Germany"}},
            {"title": "Engineer", "location": {"name": "New York, NY"}},
        ]
        match = find_north_america_job(jobs)
        self.assertIsNotNone(match)
        self.assertEqual(match[0]["title"], "Engineer")

    def test_find_north_america_job_uses_remote_fields(self):
        jobs = [
            {"title": "Engineer", "workplaceType": "remote"},
            {"title": "Designer", "isRemote": True},
        ]
        match = find_north_america_job(jobs)
        self.assertIsNotNone(match)
        self.assertEqual(match[0]["title"], "Engineer")

    def test_workday_location_facets_are_treated_as_openings(self):
        jobs = workday_location_facet_jobs([
            {
                "facetParameter": "locationMainGroup",
                "values": [
                    {
                        "facetParameter": "locationHierarchy1",
                        "descriptor": "Locations",
                        "values": [
                            {"descriptor": "Germany", "count": 3},
                            {"descriptor": "United States", "count": 4},
                        ],
                    }
                ],
            }
        ])

        match = find_north_america_job(jobs)
        self.assertIsNotNone(match)
        self.assertEqual(match[1], "United States")


class TestNorthAmericaResultStatus(unittest.TestCase):
    def test_missing_north_america_opening_is_a_failure(self):
        result = Result("Acme", "acme")
        result.probes = [
            Probe("domain_reachable", True),
            Probe("careers_url_reachable", True),
            Probe("ats:greenhouse:acme", True),
            Probe("north_america_opening", False),
        ]
        self.assertEqual(result.status, "fail")


class TestNorthAmericaProbe(unittest.IsolatedAsyncioTestCase):
    async def test_probe_passes_when_supported_ats_has_na_job(self):
        company = {"name": "Acme", "slug": "acme", "ats": {"greenhouse": "acme"}}
        jobs = [{"title": "Engineer", "location": {"name": "Vancouver"}}]
        with patch("verify_live.provider_jobs", new=AsyncMock(return_value=(jobs, "ok"))):
            probe = await probe_north_america_opening(MagicMock(), company, 0)

        self.assertTrue(probe.ok)
        self.assertEqual(probe.rule, "north_america_opening")
        self.assertIn("Engineer", probe.detail)

    async def test_probe_fails_when_no_na_job_exists(self):
        company = {"name": "Acme", "slug": "acme", "ats": {"greenhouse": "acme"}}
        jobs = [{"title": "Engineer", "location": {"name": "Berlin, Germany"}}]
        with patch("verify_live.provider_jobs", new=AsyncMock(return_value=(jobs, "ok"))):
            probe = await probe_north_america_opening(MagicMock(), company, 0)

        self.assertFalse(probe.ok)
        self.assertIn("no North America location", probe.detail)


if __name__ == "__main__":
    unittest.main()
