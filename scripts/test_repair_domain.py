import unittest
from repair_domain import host_base

class TestHostBase(unittest.TestCase):
    def test_standard_domains(self):
        self.assertEqual(host_base("example.com"), "example")
        self.assertEqual(host_base("careers.appian.com"), "appian")
        self.assertEqual(host_base("blog.succinct.xyz"), "succinct")

    def test_second_level_tlds(self):
        self.assertEqual(host_base("plinth.org.uk"), "plinth")
        self.assertEqual(host_base("example.co.jp"), "example")
        self.assertEqual(host_base("jobs.example.com.au"), "example")
        self.assertEqual(host_base("careers.example.co.uk"), "example")

    def test_www_prefix(self):
        self.assertEqual(host_base("www.example.com"), "example")
        self.assertEqual(host_base("www.careers.appian.com"), "appian")
        self.assertEqual(host_base("www.example.co.jp"), "example")

    def test_edge_cases(self):
        self.assertEqual(host_base("localhost"), "localhost")
        self.assertEqual(host_base(""), "")
        self.assertEqual(host_base("com"), "com")
        self.assertEqual(host_base("example"), "example")

if __name__ == "__main__":
    unittest.main()
