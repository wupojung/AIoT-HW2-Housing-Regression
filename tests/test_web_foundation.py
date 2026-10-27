import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.sections = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])
        if tag == "section":
            self.sections += 1

    def handle_data(self, data):
        self.text.append(data)


class WebFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (WEB / "index.html").read_text(encoding="utf-8")
        cls.css = (WEB / "styles.css").read_text(encoding="utf-8")
        cls.js = (WEB / "app.js").read_text(encoding="utf-8")
        cls.parser = SiteParser()
        cls.parser.feed(cls.html)

    def test_primary_sections_and_navigation_targets_exist(self):
        expected = {"main", "app", "case-context", "case-select", "phase-nav"}
        self.assertTrue(expected.issubset(self.parser.ids))
        self.assertIn("phase-${phase}", self.js)
        self.assertIn('data-crisp-link', self.html)

    def test_brand_course_and_project_links_are_present(self):
        text = " ".join(self.parser.text)
        self.assertIn("RegScope", text)
        self.assertIn("CRISP-DM", text)
        self.assertTrue(any("github.com/wupojung/AIoT-HW2-Housing-Regression" in href for href in self.parser.links))

    def test_unbuilt_analysis_sections_are_clearly_marked(self):
        text = (" ".join(self.parser.text) + self.js).lower()
        self.assertIn("mock", text)
        self.assertIn("not approved research results", text)
        self.assertIn("publication review remains pending", text)

    def test_responsive_navigation_and_reduced_motion_rules_exist(self):
        self.assertIn("@media (max-width: 700px)", self.css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
        self.assertIn('id="phase-nav"', self.html)
        self.assertIn('case-select', self.js)
        self.assertIn('data-dashboard-mode', self.js)

    def test_vercel_serves_only_the_static_web_directory(self):
        import json

        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(config["outputDirectory"], "web")


if __name__ == "__main__":
    unittest.main()
