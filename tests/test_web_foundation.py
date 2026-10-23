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
        expected = {"top", "main", "overview", "feature-selection", "evaluation", "research"}
        self.assertTrue(expected.issubset(self.parser.ids))
        self.assertGreaterEqual(self.parser.sections, 6)
        for href in self.parser.links:
            if href.startswith("#"):
                self.assertIn(href[1:], self.parser.ids, f"Missing navigation target: {href}")

    def test_brand_course_and_project_links_are_present(self):
        text = " ".join(self.parser.text)
        self.assertIn("RegScope", text)
        self.assertIn("Regression Analysis Showcase", text)
        self.assertIn("NCHU AIoT 2026", text)
        self.assertTrue(any("github.com/wupojung/AIoT-HW2-Housing-Regression" in href for href in self.parser.links))

    def test_unbuilt_analysis_sections_are_clearly_marked(self):
        text = " ".join(self.parser.text).lower()
        self.assertIn("coming soon", text)
        self.assertIn("no scores are published yet", text)
        self.assertNotRegex(text, re.compile(r"(?:rmse|r²|r\^2)\s*[:=]?\s*\d", re.IGNORECASE))

    def test_responsive_navigation_and_reduced_motion_rules_exist(self):
        self.assertIn("@media (max-width: 700px)", self.css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
        self.assertIn('aria-expanded', self.js)
        self.assertIn('is-open', self.js)

    def test_vercel_serves_only_the_static_web_directory(self):
        import json

        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(config["outputDirectory"], "web")


if __name__ == "__main__":
    unittest.main()
